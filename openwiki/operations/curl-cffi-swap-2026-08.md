---
type: "Reference"
title: "curl_cffi Swap — 2026-08-01"
description: "Why the scraper HTTP client switched from bare httpx to a curl_cffi-backed shim, what changed, probe results, and known caveats."
openwiki_generated: false
---

# curl_cffi Swap — 2026-08-01

> **Status (2026-08-01)**: Implemented and verified. The shim lives at
> `src/kissaten/scrapers/_curl_http.py` (~250 LOC) and is imported as
> `from . import _curl_http as httpx` by `base.py` and `shopify_base.py`.
> All 110 unit tests pass; live probes against Cartwheel, Elsewhere, and
> Archers return 200 + valid JSON on the first call from the same network
> that was returning bare `httpx` 429s. Playwright remains as the
> escalation path for the remaining hosts whose fingerprint throttle is
> stricter.

## TL;DR

Bare `httpx` (the Python `httpx` library's default TLS/HTTP2 stack) gets
HTTP 429 from a large fraction of Shopify `/products.json` endpoints when
called from the project's outbound network — the response body is the literal 18-byte
string `local_rate_limited`, returned before any HTML. Switching to
[`curl_cffi`](https://github.com/yifeikong/curl_cffi) (libcurl under the
hood) gets 200 with valid JSON from the same URLs on the same network
path.

Rather than rewrite every scraper call site, we added a thin shim that
exposes the httpx-shaped names the scrapers use (`AsyncClient`, `Auth`,
`HTTPStatusError`, `RequestError`) backed by `curl_cffi.requests.AsyncSession`.
`from . import _curl_http as httpx` replaces `import httpx` in
`base.py` and `shopify_base.py`; the rest of the code (auth flows,
exception handling, the Playwright escalation ladder) is unchanged.

`httpx` is still installed and used by the API/services layer
(`api/podcast_db.py`, `api/fx.py`, `services/geocoding.py`); only the
scrapers package swapped.

## Why bare httpx was failing

Shopify's edge returns a 429 with body `local_rate_limited` (18 bytes,
plain text) for a non-trivial fraction of `/products.json` requests. The
throttle is **fingerprint-shaped**, not IP-shaped:

- The same IP behind the same proxy can hit the same URL with
  `curl_cffi` and get 200.
- The same IP without a proxy, with the Playwright Chromium stack, also
  gets 200.
- Bare `httpx` from the same machine on the same network gets 429.

This was first observed in the 2026-07-30 batch log analysis (see
[Playwright 429 Escalation Investigation — 2026-07-30](playwright-escalation-investigation-2026-07.md))
where a long list of Shopify scrapers were chronically escalating to
Playwright. The escalation helped (Playwright's fingerprint passes) but
the 35s of wasted httpx backoff before escalation was the load-bearing
problem. Even after the 2026-07-31 ladder fix, every Shopify scraper
still paid a 5s httpx-429 → Playwright round trip on first contact.

## Probe results (2026-08-01, dev environment)

```python
# All three calls use the same Python process, same network path, same UA.
```

| URL | httpx (default) | httpx (IPv4 forced) | curl_cffi (no impersonate) |
|---|---|---|---|
| `cartwheelcoffee.com/collections/all/products.json?limit=250` | 429 `local_rate_limited` | 429 `local_rate_limited` | **200, 51 products, valid JSON** |
| `elsewherecoffee.com/collections/everything/products.json?limit=250` | 429 `local_rate_limited` | 429 `local_rate_limited` | **200, 27 products, valid JSON** |

curl_cffi without impersonation works. Forcing the scraper's
`User-Agent: "Kissaten Coffee Scraper 1.0 (github.com/dldx/kissaten)"`
header on httpx did not change the result — confirming the throttle
is on the TLS/HTTP2 fingerprint, not the UA string.

Why curl_cffi works: it uses libcurl with a different TLS stack (and
HTTP/2 settings) than Python's `httpx` (which uses `httpcore` +
`h2`/`ssl`). Shopify's edge classifies the two stacks into different
fingerprint buckets; the curl_cffi bucket is not currently throttled.

## What changed

### Code

- **`src/kissaten/scrapers/_curl_http.py`** (new, ~250 LOC) — the shim.
  Exposes `AsyncClient`, `Auth`, `HTTPStatusError`, `RequestError`.
  `AsyncClient.get()` drives any `auth_flow` per request, merges the
  resulting headers, and delegates to `curl_cffi.requests.AsyncSession`.
  curl_cffi exceptions are normalised to `RequestError`;
  `HTTPStatusError` is raised via `Response.raise_for_status()` on 4xx/5xx.
- **`src/kissaten/scrapers/base.py:17`** — `import httpx` →
  `from . import _curl_http as httpx`. Nothing else changes; `WebBotAuth`
  (subclass of `httpx.Auth`) keeps working because the shim defines an
  `Auth` base class with the same `auth_flow` contract.
- **`src/kissaten/scrapers/shopify_base.py:9`** — same one-line swap.
- **`src/kissaten/scrapers/naughty_dog.py:19`** — same one-line swap +
  `httpx.HTTPError` → `httpx.HTTPStatusError` (the shim exposes
  `HTTPStatusError`; bare `httpx`'s `HTTPError` base class was unused
  elsewhere).
- **`pyproject.toml`** — `curl-cffi>=0.16.0` added as a required dep.

### Tests

- **`tests/unit/test_shopify_scraper.py`** — added a `_StubResponse`
  helper and `_install_client_stub` helper that replaces
  `scraper.client.get` with an async stub returning canned responses.
  All eight `httpx.MockTransport`-based tests were rewritten to use
  the stub. The escalation-ladder assertions are unchanged: still
  exactly 1 shim attempt before Playwright, still per-page reset of
  the force-playwright flag, etc.
- **`tests/unit/test_out_of_stock_guard.py`** — `httpx.ConnectError`
  replaced with the shim's `RequestError`.
- **`tests/unit/test_web_bot_auth_injected`** — captures the merged
  headers by patching `scraper.client._session.get` (the shim's
  underlying curl_cffi session) rather than via `httpx.MockTransport`.

### Out of scope

- `src/kissaten/api/podcast_db.py`, `src/kissaten/api/fx.py`,
  `src/kissaten/services/geocoding.py` — still use bare `httpx`. These
  are API/services, not scrapers, and aren't throttled. Swapping them
  would be a separate change.

## Shim surface (api stability)

The shim implements only the httpx surface the scrapers actually touch.
Anything not listed below is intentionally absent.

| Used by scrapers | Shim provides |
|---|---|
| `httpx.AsyncClient(headers, timeout, follow_redirects, proxy, auth)` | ✓ (all kwargs accepted; `follow_redirects` always on) |
| `client.get(url)` → response with `.status_code`, `.text`, `.content`, `.headers`, `.json()`, `.raise_for_status()` | ✓ |
| `client.aclose()` | ✓ (wraps `curl_cffi.AsyncSession.close()`) |
| `client.__aenter__` / `__aexit__` | ✓ |
| `httpx.Auth` subclass with `auth_flow(request)` | ✓ (shim drives `auth_flow` per request, merges headers) |
| `httpx.HTTPStatusError` (with `.response`) | ✓ (raised by `raise_for_status()` on ≥400) |
| `httpx.RequestError` (parent of transport errors) | ✓ (one class wrapping all curl_cffi exceptions) |
| `httpx.Response` (`httpx.MockTransport`) | ✗ — tests use the `_StubResponse` helper instead |
| Streaming (`client.stream`), cookies, files, multipart, etc. | ✗ — add on demand |

## Behavior before / after (live probes, 2026-08-01)

End-to-end via the actual `CartwheelCoffeeScraper` and
`ElsewhereCoffeeScraper` classes:

| Scraper | Before (bare httpx) | After (curl_cffi shim) |
|---|---|---|
| Cartwheel | 429 → escalate to Playwright (~5s backoff, 1 Playwright call) | 200 on first call, 5 products, no Playwright |
| Elsewhere | 429 → escalate to Playwright | 200 on first call, 5 products, no Playwright |
| Archers (was working) | 200 on first call | 200 on first call (unchanged) |

## Why not also swap the API/services layer?

`api/podcast_db.py`, `api/fx.py`, `services/geocoding.py` use httpx for
backend HTTP services (podcast feeds, FX rates, geocoding). None of
those have been observed to 429 us — the throttling is specific to
Shopify's `/products.json` edge, not a property of bare httpx in
general. Swapping those would be a separate decision and adds curl_cffi
as a runtime dep for code paths that don't need it. Left alone for now.

## Known caveats

- **`curl_cffi` is a native extension** (libcurl bindings via
  `pycares`/`brotli`). Adds ~10 MB to the install. Already offset by
  Playwright's bundled Chromium, so the marginal size is small.
- **AsyncSession concurrency** is safe (verified with three concurrent
  `get()` calls against `example.com`). The scraper uses
  `asyncio.Semaphore(2)` to bound fan-out, so concurrent load is low.
- **Brotli decoding** is automatic (curl_cffi ships with brotli). Bare
  httpx would have errored on `Content-Encoding: br`. The shim's
  `Response.text` and `Response.content` work without extra config.
- **Web Bot Auth** still works: `WebBotAuth.auth_flow()` is driven by
  the shim per request, and the merged headers flow through to the
  curl_cffi call. The `test_web_bot_auth_injected` regression test
  verifies the signed headers end up on the outgoing request.
- **429 is still possible** for some hosts whose fingerprint throttle
  is stricter than the bare-httpx bucket. Playwright remains as the
  fallback via the existing ladder in
  `ShopifyJsonScraper._fetch_page_with_escalation` and
  `BaseScraper.fetch_page_with_screenshot`. Probe hosts that still
  429 from the project's outbound network should be added to the live observation list
  and considered for `impersonate="chrome"` (shim kwarg, not yet
  exercised).

## Related work

- [Playwright 429 Escalation Investigation — 2026-07-30](playwright-escalation-investigation-2026-07.md)
  — established that the throttle is fingerprint-shaped, not IP-shaped,
  and fixed the broken escalation ladder in `ShopifyJsonScraper`.
- [Scraper Log Analysis — 2026-07 (Post-Fix)](scraper-log-analysis-2026-07-post-fix.md)
  — confirmed the post-fix ladder reduced time-to-success on the hosts
  it could reach; this swap closes the gap on the hosts it couldn't.
- `openwiki/operations/curl-cffi-swap-2026-08.md` (this doc) — the
  full change record.