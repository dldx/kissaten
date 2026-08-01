"""Drop-in replacement for the httpx subset used by scrapers, backed by curl_cffi.

Why this exists:
    Shopify's edge returns HTTP 429 ("local_rate_limited") to requests whose
    TLS/HTTP2 fingerprint matches the default Python httpx client — even with a
    custom User-Agent. curl_cffi uses libcurl under the hood with a different
    TLS stack, so the same products.json URLs come back 200 from networks that
    rate-limit httpx. We keep the rest of the scraper code httpx-shaped by
    re-exporting the names it touches (AsyncClient, Auth, HTTPStatusError,
    RequestError) from a small adapter that wraps curl_cffi.

Scope:
    Only the surface area the scrapers actually use is exposed. Streaming,
    cookies, files, multipart, and the rest of httpx are intentionally absent
    — add them on demand rather than guessing.

Compatibility notes:
    * ``httpx.Auth`` subclasses (e.g. ``WebBotAuth``) are accepted via the
      ``auth=`` kwarg; the shim drives ``auth_flow`` per request and merges
      the resulting headers into the outgoing call. curl_cffi's async API has
      no hook system, so this lives in the shim rather than in curl_cffi.
    * ``AsyncClient(impersonate=...)`` is exposed for completeness; the
      default (``None``) is libcurl's native fingerprint, which already passes
      Shopify's edge in the configurations we scrape. Set to ``"chrome"`` or
      similar if a target starts rejecting libcurl.
    * ``follow_redirects`` is accepted for source compatibility but always
      on — curl_cffi follows redirects by default and has no off-switch in
      the async client.
"""

from __future__ import annotations

from typing import Any

try:
    from curl_cffi import requests as ccreq
    from curl_cffi.requests.exceptions import (
        RequestException as _CCRequestException,
    )
except ImportError as e:  # pragma: no cover - import-time guard
    raise ImportError(
        "curl_cffi is required for the scraper HTTP client. "
        "Install it with `uv add curl-cffi` (or `pip install curl-cffi`)."
    ) from e


class HTTPStatusError(Exception):
    """httpx-shaped HTTP error, raised by ``Response.raise_for_status()``."""

    def __init__(self, message: str, *, response: _ResponseAdapter | None = None) -> None:
        super().__init__(message)
        self.response = response


class RequestError(Exception):
    """httpx-shaped transport error, raised on network / connection failures.

    Any underlying ``curl_cffi`` request exception is normalised to this
    single class so the call sites only need to catch one type. The original
    exception is chained via ``__cause__`` for debugging.
    """


class Auth:
    """Base class for httpx.Auth-style auth flows.

    Subclasses implement ``auth_flow(request)`` as a generator that yields
    one or more mutated request objects and finally yields a final request to
    send. The shim drives the flow at request time and merges any header
    mutations onto the curl_cffi request.
    """

    def auth_flow(self, request: Any):  # pragma: no cover - abstract
        raise NotImplementedError
        yield request  # makes this a generator for type checkers


class _ResponseAdapter:
    """Thin wrapper around a curl_cffi Response exposing the httpx surface
    used by the scrapers.

    Only the attributes/methods the codebase touches are implemented
    (``.status_code``, ``.text``, ``.content``, ``.headers``, ``.json()``,
    ``.raise_for_status()``). Everything else is intentionally left out so
    we don't pretend to be a full httpx.Response.
    """

    def __init__(self, resp: Any) -> None:
        self._resp = resp

    @property
    def status_code(self) -> int:
        return self._resp.status_code

    @property
    def text(self) -> str:
        return self._resp.text

    @property
    def content(self) -> bytes:
        return self._resp.content

    @property
    def headers(self) -> Any:
        return self._resp.headers

    @property
    def url(self) -> str:
        return str(self._resp.url)

    def json(self) -> Any:
        return self._resp.json()

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise HTTPStatusError(
                f"HTTP {self.status_code} for url: {self.url}",
                response=self,
            )


class _AuthRequest:
    """Minimal stand-in that mimics the ``request.headers`` interface an
    ``httpx.Auth.auth_flow`` implementation mutates.

    The shim instantiates one of these, hands it to ``auth_flow``, then
    copies any header mutations back onto the curl_cffi request.
    """

    def __init__(self, url: str, headers: dict[str, str]) -> None:
        self.url = url
        self.headers = dict(headers)


def _drive_auth(auth: Auth, url: str, base_headers: dict[str, str]) -> dict[str, str]:
    """Run an httpx.Auth-style auth_flow and return the merged header dict.

    ``auth_flow`` is a generator that yields request objects; the shim
    treats the first yielded request's headers as the initial set, and any
    subsequent mutations as overrides. We only care about the final state of
    ``request.headers`` — auth flows that yield more than one request are
    rare (mainly NTLM/Digest) and not used in this codebase.
    """
    fake = _AuthRequest(url, base_headers)
    flow = auth.auth_flow(fake)
    for _ in flow:
        # Drain the generator; we only use the final header state on ``fake``.
        pass
    return dict(fake.headers)


def _wrap_curl_error(exc: Exception) -> Exception:
    """Map a curl_cffi exception to our httpx-shaped equivalent.

    curl_cffi raises ``RequestException`` (or subclasses) for transport-level
    failures and leaves HTTP status handling to the caller. We collapse all
    transport errors to ``RequestError``; HTTPStatusError is raised
    separately by ``raise_for_status``.
    """
    if isinstance(exc, _CCRequestException):
        return RequestError(str(exc))
    # Defensive: curl_cffi occasionally raises bare CurlError or other
    # exceptions that don't inherit RequestException; treat them the same.
    return RequestError(str(exc))


class AsyncClient:
    """Drop-in replacement for ``httpx.AsyncClient`` backed by curl_cffi.

    All keyword arguments accepted here match the subset of the httpx
    signature the scrapers use. ``follow_redirects`` is always on (curl_cffi
    has no off-switch in the async client); ``impersonate`` defaults to
    ``None`` (libcurl's native fingerprint) which is sufficient for the
    scrapers' current targets.
    """

    def __init__(
        self,
        *,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        follow_redirects: bool = True,  # accepted for source compat; always on
        proxy: str | None = None,
        auth: Auth | None = None,
        impersonate: str | None = None,
    ) -> None:
        session_kwargs: dict[str, Any] = {
            "headers": dict(headers or {}),
            "timeout": timeout,
        }
        if proxy:
            session_kwargs["proxy"] = proxy
        if impersonate:
            session_kwargs["impersonate"] = impersonate

        self._session = ccreq.AsyncSession(**session_kwargs)
        self._auth = auth
        # Cache the auth object so per-request __init__ paths in tests can
        # reconstruct an equivalent client (e.g. ``scraper.client = AsyncClient(
        # auth=scraper.client.auth, ...)`` from the old test fixtures).
        self._timeout = timeout
        self._impersonate = impersonate
        self._base_headers = dict(headers or {})
        self._proxy = proxy

    async def get(self, url: str, **kwargs: Any) -> _ResponseAdapter:
        """Issue a GET and return an httpx-shaped response adapter.

        Any ``auth=`` on the client is driven first; auth headers are merged
        into the per-request header set. curl_cffi exceptions are normalised
        to our ``RequestError``; HTTPStatusError is raised via
        ``raise_for_status()`` on the returned adapter.
        """
        request_headers: dict[str, str] = dict(self._base_headers)
        per_request_headers = kwargs.pop("headers", None)
        if per_request_headers:
            request_headers.update(per_request_headers)

        if self._auth is not None:
            try:
                request_headers = _drive_auth(self._auth, url, request_headers)
            except HTTPStatusError:
                raise
            except Exception as e:
                # An auth_flow failure is a transport problem from the
                # caller's perspective.
                raise RequestError(f"auth_flow failed: {e}") from e

        try:
            resp = await self._session.get(url, headers=request_headers, **kwargs)
        except Exception as e:
            raise _wrap_curl_error(e) from e

        return _ResponseAdapter(resp)

    async def aclose(self) -> None:
        """Close the underlying curl_cffi session."""
        await self._session.close()

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.aclose()


# Re-export under the names the shim's callers expect.
__all__ = [
    "AsyncClient",
    "Auth",
    "HTTPStatusError",
    "RequestError",
]
