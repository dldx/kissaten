"""Read-only access to page-cache archives stored in Cloudflare R2.

This is the remote half of the admin page-cache viewer.  It is entirely
optional: when the ``KISSATEN_R2_*`` environment variables are missing the
helpers simply report "not available" and the viewer serves local archives.

Configuration is read at call time (not import time) so tests can monkeypatch
the environment.  Listings are cached in-process for a short TTL because the
admin viewer may be opened repeatedly.
"""

import logging
import os
import threading
import time
from datetime import datetime, timezone

from .page_cache import FILENAME_RE, SESSION_DATE_RE, CacheSnapshot

logger = logging.getLogger(__name__)

#: Refuse to download page archives larger than this (bytes).
MAX_OBJECT_SIZE = 25 * 1024 * 1024

#: Default listing cache TTL in seconds.
DEFAULT_LIST_CACHE_TTL = 300.0

_client = None
_client_config: tuple | None = None
_client_lock = threading.Lock()

# (prefix, roaster_dir) -> (monotonic fetched_at, snapshots)
_listing_cache: dict[tuple[str, str], tuple[float, list[CacheSnapshot]]] = {}
_listing_lock = threading.Lock()


def _env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def _r2_config() -> dict[str, str | None]:
    prefix = (_env("KISSATEN_R2_PREFIX", "cache") or "").strip("/")
    return {
        "endpoint": _env("KISSATEN_R2_ENDPOINT"),
        "bucket": _env("KISSATEN_R2_BUCKET"),
        "prefix": prefix,
        "access_key_id": _env("KISSATEN_R2_ACCESS_KEY_ID"),
        "secret_access_key": _env("KISSATEN_R2_SECRET_ACCESS_KEY"),
    }


def _list_cache_ttl() -> float:
    raw = _env("KISSATEN_R2_LIST_CACHE_TTL")
    if raw is None:
        return DEFAULT_LIST_CACHE_TTL
    try:
        return max(0.0, float(raw))
    except ValueError:
        return DEFAULT_LIST_CACHE_TTL


def r2_available() -> bool:
    """Return True when all required R2 credentials/endpoint are configured."""
    cfg = _r2_config()
    return bool(cfg["endpoint"] and cfg["bucket"] and cfg["access_key_id"] and cfg["secret_access_key"])


def _get_client():
    """Return the lazy boto3 S3 client for the current R2 configuration."""
    global _client, _client_config

    cfg = _r2_config()
    config_key = (
        cfg["endpoint"],
        cfg["access_key_id"],
        cfg["secret_access_key"],
    )

    with _client_lock:
        if _client is not None and _client_config == config_key:
            return _client

        # Imported lazily so local-only deployments work even without boto3.
        import boto3
        from botocore.config import Config

        _client = boto3.client(
            "s3",
            endpoint_url=cfg["endpoint"],
            region_name="auto",
            aws_access_key_id=cfg["access_key_id"],
            aws_secret_access_key=cfg["secret_access_key"],
            config=Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=5,
                read_timeout=20,
            ),
        )
        _client_config = config_key
        return _client


def _safe_roaster_dir(roaster_dir: str) -> bool:
    return bool(roaster_dir) and "/" not in roaster_dir and "\\" not in roaster_dir and roaster_dir not in {".", ".."}


def _listing_prefix(prefix: str, roaster_dir: str) -> str:
    base = f"{prefix}/" if prefix else ""
    return f"{base}roasters/{roaster_dir}/"


def _object_key(prefix: str, roaster_dir: str, session_date: str, filename: str) -> str:
    return f"{_listing_prefix(prefix, roaster_dir)}{session_date}/{filename}"


def _snapshot_from_object(prefix: str, roaster_dir: str, obj: dict) -> CacheSnapshot | None:
    """Parse a ListObjectsV2 object into a CacheSnapshot, or None if malformed."""
    key = obj.get("Key") or ""
    marker = f"roasters/{roaster_dir}/"
    idx = key.find(marker)
    if idx < 0:
        return None

    parts = key[idx + len(marker) :].split("/")
    if len(parts) != 2:
        return None

    session_date, filename = parts
    if not SESSION_DATE_RE.match(session_date) or not FILENAME_RE.match(filename):
        return None

    size = obj.get("Size")
    last_modified = obj.get("LastModified")
    if isinstance(last_modified, datetime) and last_modified.tzinfo is None:
        last_modified = last_modified.replace(tzinfo=timezone.utc)

    return CacheSnapshot(
        session_date=session_date,
        filename=filename,
        source="r2",
        size=size if isinstance(size, int) else None,
        last_modified=last_modified if isinstance(last_modified, datetime) else None,
        has_screenshot=None,
    )


def _fetch_roaster_listing(prefix: str, roaster_dir: str) -> list[CacheSnapshot]:
    """Fetch and parse every object under a roaster's R2 prefix."""
    cfg = _r2_config()
    bucket = cfg["bucket"]
    if not bucket:
        return []

    try:
        client = _get_client()
        paginator = client.get_paginator("list_objects_v2")
        snapshots: list[CacheSnapshot] = []
        for page in paginator.paginate(Bucket=bucket, Prefix=_listing_prefix(prefix, roaster_dir)):
            for obj in page.get("Contents", []) or []:
                snapshot = _snapshot_from_object(prefix, roaster_dir, obj)
                if snapshot is not None:
                    snapshots.append(snapshot)
    except Exception as exc:  # noqa: BLE001 - never fail the viewer on R2 errors
        logger.warning("Failed to list R2 page cache for %s: %s", roaster_dir, exc)
        return []

    snapshots.sort(key=lambda s: (s.session_date, s.filename), reverse=True)
    return snapshots


def _cached_roaster_listing(prefix: str, roaster_dir: str) -> list[CacheSnapshot]:
    """Return a TTL-cached listing for a roaster directory."""
    ttl = _list_cache_ttl()
    now = time.monotonic()
    key = (prefix, roaster_dir)

    with _listing_lock:
        cached = _listing_cache.get(key)
        if cached is not None and now - cached[0] < ttl:
            return cached[1]

    snapshots = _fetch_roaster_listing(prefix, roaster_dir)

    with _listing_lock:
        _listing_cache[key] = (now, snapshots)

    return snapshots


def list_r2_snapshots(roaster_dirs, filename: str) -> list[CacheSnapshot]:
    """List R2 archives matching ``filename`` across the candidate roaster dirs."""
    if not filename or not FILENAME_RE.match(filename) or not r2_available():
        return []

    prefix = _r2_config()["prefix"] or ""
    snapshots: list[CacheSnapshot] = []

    for roaster_dir in roaster_dirs:
        if not _safe_roaster_dir(roaster_dir):
            continue
        snapshots.extend(s for s in _cached_roaster_listing(prefix, roaster_dir) if s.filename == filename)

    snapshots.sort(key=lambda s: (s.session_date, s.filename), reverse=True)
    return snapshots


def read_r2_snapshot(roaster_dir: str, session_date: str, filename: str) -> bytes | None:
    """Download a single archive from R2, or ``None`` when absent/invalid/too large."""
    if not r2_available():
        return None
    if not _safe_roaster_dir(roaster_dir):
        return None
    if not SESSION_DATE_RE.match(session_date or "") or not FILENAME_RE.match(filename or ""):
        return None

    cfg = _r2_config()
    bucket = cfg["bucket"]
    if not bucket:
        return None

    key = _object_key(cfg["prefix"] or "", roaster_dir, session_date, filename)

    try:
        client = _get_client()
        obj = client.get_object(Bucket=bucket, Key=key)

        content_length = obj.get("ContentLength")
        if isinstance(content_length, int) and content_length > MAX_OBJECT_SIZE:
            logger.warning(
                "Refusing to download R2 page cache %s: %s bytes exceeds %s byte limit",
                key,
                content_length,
                MAX_OBJECT_SIZE,
            )
            return None

        body = obj.get("Body")
        if body is None:
            return None
        data = body.read(MAX_OBJECT_SIZE + 1)
    except Exception as exc:  # noqa: BLE001 - never fail the viewer on R2 errors
        logger.warning("Failed to read R2 page cache %s: %s", key, exc)
        return None

    if len(data) > MAX_OBJECT_SIZE:
        logger.warning(
            "Refusing to use R2 page cache %s: downloaded %s bytes exceeds %s byte limit",
            key,
            len(data),
            MAX_OBJECT_SIZE,
        )
        return None

    return data


def reset_r2_caches() -> None:
    """Clear the in-memory client and listing caches (test helper)."""
    global _client, _client_config
    with _client_lock:
        _client = None
        _client_config = None
    with _listing_lock:
        _listing_cache.clear()
