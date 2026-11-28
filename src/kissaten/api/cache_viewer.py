"""Admin-only API for inspecting cached raw pages.

Scrapers store every fetched page as a tarball under
``data/cache/roasters/<roaster_dir>/<YYYYMMDD>/<slug>.tar.gz`` (and optionally
mirror them to Cloudflare R2).  These endpoints expose that cache to the admin
frontend so a reviewer can compare what the scraper actually saw with the
structured bean data.

The endpoints are deliberately read-only and admin-gated.  They do not apply
the public ``requires_review`` filter: an admin needs to see the cache for every
bean, including ones still pending review.
"""

import json
import logging
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from starlette.responses import Response

from kissaten.api.db import conn
from kissaten.api.utils import slugify_roaster
from kissaten.cache import r2_page_cache
from kissaten.cache.page_cache import (
    FILENAME_RE,
    SESSION_DATE_RE,
    CacheSnapshot,
    default_cache_root,
    extract_page_cache,
    inject_base_href,
    list_local_snapshots,
    page_cache_filename,
    read_local_snapshot,
)
from kissaten.schemas import APIResponse
from kissaten.scrapers import get_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/admin/cache", tags=["admin-cache"])

ADMIN_TOKEN_ENV = "KISSATEN_ADMIN_API_TOKEN"
ADMIN_TOKEN_HEADER = "X-Kissaten-Admin-Token"

_HTML_CSP = (
    "sandbox; default-src 'none'; script-src 'none'; "
    "img-src https: http: data:; style-src https: http: 'unsafe-inline'; "
    "font-src https: http: data:; base-uri https: http:; form-action 'none'"
)

_HTML_HEADERS = {
    "Content-Security-Policy": _HTML_CSP,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "private, no-store",
}

_BINARY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "private, no-store",
}


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class CacheBeanInfo(BaseModel):
    """Identifying fields of the bean whose cache is being viewed."""

    name: str | None = None
    roaster: str | None = None
    url: str | None = None
    bean_url_path: str | None = None
    scraped_at: datetime | None = None


class CacheSnapshotModel(BaseModel):
    """A single cached archive."""

    session_date: str
    filename: str
    source: Literal["local", "r2"]
    size: int | None = None
    last_modified: datetime | None = None
    has_screenshot: bool | None = None


class CacheStorageModel(BaseModel):
    """Which storage backends are available to the viewer."""

    local: bool
    r2: bool


class CacheSnapshotsResponse(BaseModel):
    """Payload of ``GET /v1/admin/cache/beans/{roaster_slug}/{bean_slug}``."""

    bean: CacheBeanInfo
    roaster_dirs: list[str]
    snapshots: list[CacheSnapshotModel]
    storage: CacheStorageModel
    warnings: list[str]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def require_cache_admin(
    x_kissaten_admin_token: Annotated[str | None, Header(alias=ADMIN_TOKEN_HEADER)] = None,
) -> None:
    """Require the shared admin token for every cache-viewer request.

    The expected token is read from ``KISSATEN_ADMIN_API_TOKEN`` at request time
    (not import time) so deployments/tests can change it without reloading.
    """
    expected = os.environ.get(ADMIN_TOKEN_ENV)
    if not expected:
        raise HTTPException(status_code=503, detail="Cache viewer is not configured.")
    if not x_kissaten_admin_token or not secrets.compare_digest(x_kissaten_admin_token, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing admin token.")


# ---------------------------------------------------------------------------
# Bean + snapshot resolution
# ---------------------------------------------------------------------------


def _lookup_bean(roaster_slug: str, bean_slug: str) -> dict | None:
    """Fetch the newest bean row for ``/{roaster_slug}/{bean_slug}``."""
    expected_path = f"/{roaster_slug}/{bean_slug}"
    query = """
        SELECT name, roaster, url, bean_url_path, scraped_at
        FROM coffee_beans
        WHERE bean_url_path = ?
        ORDER BY scraped_at DESC
        LIMIT 1
    """

    result = conn.execute(query, [expected_path]).fetchone()
    if not result:
        # Tolerate the rare rows whose bean_url_path lacks the leading slash.
        result = conn.execute(query, [expected_path.lstrip("/")]).fetchone()
    if not result:
        return None

    columns = ["name", "roaster", "url", "bean_url_path", "scraped_at"]
    return dict(zip(columns, result))


def _candidate_roaster_dirs(roaster_name: str | None, bean_url_path: str | None) -> list[str]:
    """Build the ordered, de-duplicated list of roaster directory names to scan."""
    candidates: list[str] = []

    if roaster_name:
        try:
            registry = get_registry()
            for info in registry.list_scrapers():
                if info.roaster_name == roaster_name:
                    candidates.append(info.directory_name)
                    break
        except Exception as exc:  # noqa: BLE001 - registry lookup is best-effort
            logger.debug("Registry lookup failed for roaster %r: %s", roaster_name, exc)

        try:
            candidates.append(slugify_roaster(roaster_name))
        except Exception as exc:  # noqa: BLE001 - slugify is best-effort
            logger.debug("Could not slugify roaster %r: %s", roaster_name, exc)

    if bean_url_path:
        first_segment = bean_url_path.strip("/").split("/", 1)[0]
        if first_segment:
            candidates.append(first_segment)

    seen: set[str] = set()
    ordered: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def _snapshot_model(snapshot: CacheSnapshot) -> CacheSnapshotModel:
    return CacheSnapshotModel(
        session_date=snapshot.session_date,
        filename=snapshot.filename,
        source=snapshot.source,
        size=snapshot.size,
        last_modified=snapshot.last_modified,
        has_screenshot=snapshot.has_screenshot,
    )


def _gather_snapshots(
    cache_root: Path,
    roaster_dirs: list[str],
    filename: str,
) -> tuple[list[CacheSnapshot], CacheStorageModel, list[str]]:
    """Merge local and R2 snapshots, preferring local on conflict."""
    warnings: list[str] = []

    local_snapshots = list_local_snapshots(cache_root, roaster_dirs, filename)

    remote_snapshots: list[CacheSnapshot] = []
    if r2_page_cache.r2_available():
        try:
            remote_snapshots = r2_page_cache.list_r2_snapshots(roaster_dirs, filename)
        except Exception as exc:  # noqa: BLE001 - local cache must still work
            logger.warning("R2 page-cache listing failed: %s", exc)
            warnings.append("Remote cache listing failed; showing local snapshots only.")

    merged: dict[tuple[str, str], CacheSnapshot] = {}
    for snapshot in remote_snapshots:
        merged[(snapshot.session_date, snapshot.filename)] = snapshot
    # Local wins on conflict.
    for snapshot in local_snapshots:
        merged[(snapshot.session_date, snapshot.filename)] = snapshot

    ordered = sorted(merged.values(), key=lambda s: (s.session_date, s.filename), reverse=True)

    if not ordered:
        warnings.append("No cached snapshots found for this bean.")

    storage = CacheStorageModel(local=cache_root.exists(), r2=r2_page_cache.r2_available())
    return ordered, storage, warnings


def _read_raw_snapshot(
    cache_root: Path,
    roaster_dirs: list[str],
    session_date: str,
    filename: str,
) -> bytes | None:
    """Read an archive from local storage first, then fall back to R2."""
    for roaster_dir in roaster_dirs:
        raw = read_local_snapshot(cache_root, roaster_dir, session_date, filename)
        if raw is not None:
            return raw

    if r2_page_cache.r2_available():
        for roaster_dir in roaster_dirs:
            raw = r2_page_cache.read_r2_snapshot(roaster_dir, session_date, filename)
            if raw is not None:
                return raw

    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/beans/{roaster_slug}/{bean_slug}", response_model=APIResponse[CacheSnapshotsResponse])
def list_cache_snapshots(
    roaster_slug: str,
    bean_slug: str,
    _admin: None = Depends(require_cache_admin),
) -> APIResponse[CacheSnapshotsResponse]:
    """List the cached raw-page snapshots available for a bean."""
    bean = _lookup_bean(roaster_slug, bean_slug)
    if bean is None:
        raise HTTPException(
            status_code=404,
            detail=f"Bean '{bean_slug}' not found for roaster '{roaster_slug}'",
        )

    cache_root = default_cache_root()
    filename = page_cache_filename(bean.get("url") or "")
    roaster_dirs = _candidate_roaster_dirs(bean.get("roaster"), bean.get("bean_url_path"))

    snapshots, storage, warnings = _gather_snapshots(cache_root, roaster_dirs, filename)

    data = CacheSnapshotsResponse(
        bean=CacheBeanInfo(
            name=bean.get("name"),
            roaster=bean.get("roaster"),
            url=bean.get("url"),
            bean_url_path=bean.get("bean_url_path"),
            scraped_at=bean.get("scraped_at"),
        ),
        roaster_dirs=roaster_dirs,
        snapshots=[_snapshot_model(snapshot) for snapshot in snapshots],
        storage=storage,
        warnings=warnings,
    )
    return APIResponse.success_response(data=data)


@router.get("/beans/{roaster_slug}/{bean_slug}/content")
def get_cache_content(
    roaster_slug: str,
    bean_slug: str,
    session_date: Annotated[str, Query(alias="session", description="Snapshot session date (YYYYMMDD)")],
    filename: Annotated[str, Query(description="Cache archive filename")],
    kind: Annotated[Literal["html", "screenshot", "metadata", "raw"], Query()] = "html",
    _admin: None = Depends(require_cache_admin),
) -> Response:
    """Serve the HTML, screenshot, metadata or raw archive of a cached page."""
    if not SESSION_DATE_RE.match(session_date or ""):
        raise HTTPException(status_code=400, detail="Invalid session date; expected YYYYMMDD.")
    if not FILENAME_RE.match(filename or ""):
        raise HTTPException(status_code=400, detail="Invalid cache filename.")

    bean = _lookup_bean(roaster_slug, bean_slug)
    if bean is None:
        raise HTTPException(
            status_code=404,
            detail=f"Bean '{bean_slug}' not found for roaster '{roaster_slug}'",
        )

    cache_root = default_cache_root()
    bean_url = bean.get("url") or ""
    bean_filename = page_cache_filename(bean_url)
    roaster_dirs = _candidate_roaster_dirs(bean.get("roaster"), bean.get("bean_url_path"))

    snapshots, _, _ = _gather_snapshots(cache_root, roaster_dirs, bean_filename)
    available = {(snapshot.session_date, snapshot.filename) for snapshot in snapshots}
    if (session_date, filename) not in available:
        raise HTTPException(status_code=404, detail="Cached snapshot not found for this bean.")

    raw = _read_raw_snapshot(cache_root, roaster_dirs, session_date, filename)
    if raw is None:
        raise HTTPException(status_code=404, detail="Cached snapshot could not be read.")

    if kind == "raw":
        return Response(
            content=raw,
            media_type="application/gzip",
            headers={
                **_BINARY_HEADERS,
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    metadata, html, screenshot = extract_page_cache(raw)

    if kind == "html":
        if html is None:
            raise HTTPException(status_code=404, detail="Cached snapshot has no HTML.")
        return Response(content=inject_base_href(html, bean_url), media_type="text/html", headers=_HTML_HEADERS)

    if kind == "screenshot":
        if screenshot is None:
            raise HTTPException(status_code=404, detail="Cached snapshot has no screenshot.")
        return Response(content=screenshot, media_type="image/png", headers=_BINARY_HEADERS)

    # kind == "metadata"
    return Response(
        content=json.dumps(metadata),
        media_type="application/json",
        headers=_BINARY_HEADERS,
    )
