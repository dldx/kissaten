"""Shared helpers for raw page-cache archives.

Scrapers cache the raw HTML (and optional screenshot) of every fetched page as a
self-contained ``<slug>.tar.gz`` archive under
``data/cache/roasters/<roaster_dir>/<YYYYMMDD>/``.  This module centralises the
filename convention and the read-side helpers so the scraper write path and the
admin cache viewer can never drift apart.

The module intentionally depends only on the standard library: it must be safe
to import from ``kissaten.scrapers.base`` without pulling in the API (and so
creating an import cycle).
"""

import hashlib
import io
import json
import logging
import os
import re
import tarfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
from pathlib import Path, PurePosixPath
from typing import Literal
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

#: Default cache root when ``KISSATEN_CACHE_DIR`` is not set.
DEFAULT_CACHE_DIR = Path("data/cache")

#: A session directory is always a ``YYYYMMDD`` date string.
SESSION_DATE_RE = re.compile(r"^\d{8}$")

#: Cache archives produced by :func:`page_cache_filename`.
FILENAME_RE = re.compile(r"^[a-z0-9_.-]+\.tar\.gz$")

_SAFE_ROASTER_DIR_RE = re.compile(r"^[^/\\\x00]+$")


@dataclass
class CacheSnapshot:
    """A single cached page archive (local or remote).

    Attributes:
        session_date: Session directory name (``YYYYMMDD``).
        filename: Archive filename, e.g. ``my-bean.tar.gz``.
        source: Where the snapshot was found (``"local"`` or ``"r2"``).
        size: Archive size in bytes, when known.
        last_modified: Modification time, when known.
        has_screenshot: Whether the archive contains a screenshot.  Listings may
            leave this as ``None`` because it requires opening the archive.
    """

    session_date: str
    filename: str
    source: Literal["local", "r2"]
    size: int | None = None
    last_modified: datetime | None = None
    has_screenshot: bool | None = None


def page_cache_filename(url: str) -> str:
    """Generate the cache filename for a page URL.

    This mirrors :meth:`kissaten.scrapers.base.BaseScraper._get_cache_filename`
    exactly: use the last meaningful URL path segment, strip a trailing
    ``.html`` / ``.php``, lowercase, replace any character outside
    ``[a-z0-9_-]`` with ``_`` and append ``.tar.gz``.  URLs without a path fall
    back to the first 8 hex characters of the URL's md5 digest.
    """
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split("/") if p]

    if path_parts:
        slug = path_parts[-1].replace(".html", "").replace(".php", "")
        slug = re.sub(r"[^a-z0-9_-]", "_", slug.lower())
    else:
        slug = hashlib.md5(url.encode()).hexdigest()[:8]

    return f"{slug}.tar.gz"


def default_cache_root() -> Path:
    """Return the configured cache root (``KISSATEN_CACHE_DIR`` or ``data/cache``)."""
    configured = os.environ.get("KISSATEN_CACHE_DIR")
    return Path(configured) if configured else DEFAULT_CACHE_DIR


def _safe_roaster_dir(roaster_dir: str) -> bool:
    """Return True when ``roaster_dir`` is a single, non-traversing path segment."""
    return bool(roaster_dir) and bool(_SAFE_ROASTER_DIR_RE.match(roaster_dir)) and roaster_dir not in {".", ".."}


def _resolve_local_path(
    cache_root: Path | str,
    roaster_dir: str,
    session_date: str,
    filename: str,
) -> Path | None:
    """Resolve a local archive path, refusing anything outside ``cache_root``."""
    if not SESSION_DATE_RE.match(session_date or ""):
        return None
    if not FILENAME_RE.match(filename or ""):
        return None
    if not _safe_roaster_dir(roaster_dir):
        return None

    root = Path(cache_root).resolve()
    candidate = (root / "roasters" / roaster_dir / session_date / filename).resolve()

    try:
        candidate.relative_to(root)
    except ValueError:
        return None

    if not candidate.is_file():
        return None
    return candidate


def list_local_snapshots(
    cache_root: Path | str,
    roaster_dirs: Iterable[str],
    filename: str,
) -> list[CacheSnapshot]:
    """List local archives matching ``filename`` across the candidate roaster dirs.

    Each candidate is joined explicitly (no glob) and only session directories
    matching ``^\\d{8}$`` are considered.
    """
    if not FILENAME_RE.match(filename or ""):
        return []

    root = Path(cache_root).resolve()
    snapshots: list[CacheSnapshot] = []

    for roaster_dir in roaster_dirs:
        if not _safe_roaster_dir(roaster_dir):
            continue

        roaster_path = root / "roasters" / roaster_dir
        try:
            session_entries = list(roaster_path.iterdir())
        except OSError:
            continue

        for session_path in session_entries:
            if not SESSION_DATE_RE.match(session_path.name) or not session_path.is_dir():
                continue

            candidate = session_path / filename
            try:
                stat = candidate.stat()
            except OSError:
                continue

            if not candidate.is_file():
                continue

            snapshots.append(
                CacheSnapshot(
                    session_date=session_path.name,
                    filename=filename,
                    source="local",
                    size=stat.st_size,
                    last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                    has_screenshot=None,
                )
            )

    snapshots.sort(key=lambda s: (s.session_date, s.filename), reverse=True)
    return snapshots


def read_local_snapshot(
    cache_root: Path | str,
    roaster_dir: str,
    session_date: str,
    filename: str,
) -> bytes | None:
    """Read a local archive, or ``None`` when absent/unsafe/unreadable."""
    path = _resolve_local_path(cache_root, roaster_dir, session_date, filename)
    if path is None:
        return None

    try:
        return path.read_bytes()
    except OSError as exc:
        logger.warning("Failed to read local page cache %s: %s", path, exc)
        return None


def extract_page_cache(raw: bytes) -> tuple[dict, str | None, bytes | None]:
    """Extract ``(metadata, html, screenshot)`` from archive bytes.

    Members are read individually; ``extractall`` is never used so archive
    paths cannot touch the filesystem.
    """
    metadata: dict = {}
    html: str | None = None
    screenshot: bytes | None = None

    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue

                member_name = PurePosixPath(member.name).name
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                data = extracted.read()

                if member_name == "metadata.json":
                    try:
                        loaded = json.loads(data.decode("utf-8"))
                    except (UnicodeDecodeError, ValueError):
                        loaded = {}
                    if isinstance(loaded, dict):
                        metadata = loaded
                elif member_name == "page.html":
                    html = data.decode("utf-8", errors="replace")
                elif member_name == "screenshot.png":
                    screenshot = data
    except (tarfile.TarError, OSError, EOFError) as exc:
        logger.warning("Failed to extract page cache archive: %s", exc)
        return {}, None, None

    return metadata, html, screenshot


def inject_base_href(html: str, base_url: str) -> str:
    """Insert ``<base href="...">`` so relative assets resolve against ``base_url``.

    The tag is inserted at the start of ``<head>`` when present, otherwise just
    before ``</head>``, otherwise prepended to the document.
    """
    base_tag = f'<base href="{escape(base_url or "", quote=True)}">'

    head_match = re.search(r"<head\b[^>]*>", html, flags=re.IGNORECASE)
    if head_match:
        idx = head_match.end()
        return html[:idx] + base_tag + html[idx:]

    close_match = re.search(r"</head\s*>", html, flags=re.IGNORECASE)
    if close_match:
        idx = close_match.start()
        return html[:idx] + base_tag + html[idx:]

    return base_tag + html
