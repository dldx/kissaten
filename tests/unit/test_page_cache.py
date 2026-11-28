"""Unit tests for shared page-cache helpers."""

import hashlib
import io
import json
import tarfile

import pytest

from kissaten.cache.page_cache import (
    extract_page_cache,
    inject_base_href,
    list_local_snapshots,
    page_cache_filename,
    read_local_snapshot,
)
from kissaten.scrapers.base import BaseScraper


class _TestScraper(BaseScraper):
    """Concrete shell so we can call ``_get_cache_filename`` without __init__."""

    async def get_store_urls(self) -> list[str]:  # pragma: no cover - never called
        return []

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:  # pragma: no cover - never called
        return []


# ``_get_cache_filename`` does not read instance state, so a bare instance is
# enough to pin parity without running the scraper's network-heavy __init__.
_SCRAPER = object.__new__(_TestScraper)


def _make_archive(
    html: str | bytes = "<html><head></head><body>hello</body></html>",
    screenshot: bytes | None = b"PNGDATA",
    metadata: dict | None = None,
) -> bytes:
    """Build a cache tarball in memory."""
    html_bytes = html.encode("utf-8") if isinstance(html, str) else html
    entries: list[tuple[str, bytes]] = [
        ("metadata.json", json.dumps(metadata if metadata is not None else {"url": "https://example.com"}).encode("utf-8")),
        ("page.html", html_bytes),
    ]
    if screenshot is not None:
        entries.append(("screenshot.png", screenshot))

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, data in entries:
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/products/ethiopia-yirgacheffe",
        "https://example.com/product.html",
        "https://example.com/product.php",
        "https://example.com/products/bean/",
        "https://example.com/",
        "https://example.com",
        "https://example.com/Products/My Bean",
        "https://example.com/products/caf%C3%A9?foo=bar",
        "https://example.com/a/b/c.HTML",
    ],
)
def test_filename_matches_base_scraper(url: str) -> None:
    assert page_cache_filename(url) == _SCRAPER._get_cache_filename(url)


def test_filename_specific_values() -> None:
    assert page_cache_filename("https://example.com/product.html") == "product.tar.gz"
    assert page_cache_filename("https://example.com/product.php") == "product.tar.gz"
    assert page_cache_filename("https://example.com/products/my-bean") == "my-bean.tar.gz"
    assert page_cache_filename("https://example.com/Products/My Bean") == "my_bean.tar.gz"

    homepage = page_cache_filename("https://example.com/")
    expected_hash = hashlib.md5(b"https://example.com/").hexdigest()[:8]
    assert homepage == f"{expected_hash}.tar.gz"


def test_list_and_read_local_snapshots(tmp_path) -> None:
    cache_root = tmp_path / "cache"
    session_dir = cache_root / "roasters" / "test_roaster" / "20240101"
    session_dir.mkdir(parents=True)
    archive = _make_archive()
    (session_dir / "bean.tar.gz").write_bytes(archive)

    # A non-date directory and a different filename must be ignored.
    other_dir = cache_root / "roasters" / "test_roaster" / "not-a-session"
    other_dir.mkdir(parents=True)
    (other_dir / "bean.tar.gz").write_bytes(b"ignored")
    (session_dir / "other.tar.gz").write_bytes(b"ignored")

    snapshots = list_local_snapshots(cache_root, ["test_roaster"], "bean.tar.gz")

    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot.session_date == "20240101"
    assert snapshot.filename == "bean.tar.gz"
    assert snapshot.source == "local"
    assert snapshot.size == len(archive)
    assert snapshot.last_modified is not None
    assert snapshot.has_screenshot is None

    assert read_local_snapshot(cache_root, "test_roaster", "20240101", "bean.tar.gz") == archive


def test_list_local_snapshots_missing_root(tmp_path) -> None:
    assert list_local_snapshots(tmp_path / "does-not-exist", ["roaster"], "bean.tar.gz") == []


def test_list_local_snapshots_rejects_bad_filename(tmp_path) -> None:
    cache_root = tmp_path / "cache"
    (cache_root / "roasters" / "test_roaster" / "20240101").mkdir(parents=True)
    assert list_local_snapshots(cache_root, ["test_roaster"], "../bean.tar.gz") == []


@pytest.mark.parametrize(
    ("roaster_dir", "session_date", "filename"),
    [
        ("../evil", "20240101", "bean.tar.gz"),
        ("test_roaster", "../20240101", "bean.tar.gz"),
        ("test_roaster", "..", "../../bean.tar.gz"),
        ("test_roaster", "20240101", "../bean.tar.gz"),
        ("test_roaster", "20240101", "nested/bean.tar.gz"),
        ("..", "20240101", "bean.tar.gz"),
    ],
)
def test_read_local_snapshot_rejects_traversal(tmp_path, roaster_dir, session_date, filename) -> None:
    cache_root = tmp_path / "cache"
    (cache_root / "roasters" / "test_roaster" / "20240101").mkdir(parents=True)

    assert read_local_snapshot(cache_root, roaster_dir, session_date, filename) is None


def test_read_local_snapshot_rejects_symlink_escape(tmp_path) -> None:
    cache_root = tmp_path / "cache"
    session_dir = cache_root / "roasters" / "test_roaster" / "20240101"
    session_dir.mkdir(parents=True)

    outside = tmp_path / "outside.tar.gz"
    outside.write_bytes(b"secret")
    (session_dir / "bean.tar.gz").symlink_to(outside)

    assert read_local_snapshot(cache_root, "test_roaster", "20240101", "bean.tar.gz") is None


def test_extract_page_cache_all_members() -> None:
    metadata, html, screenshot = extract_page_cache(
        _make_archive(
            html="<html><head></head><body>hi</body></html>",
            screenshot=b"PNGDATA",
            metadata={"url": "https://example.com/bean"},
        )
    )

    assert metadata == {"url": "https://example.com/bean"}
    assert html == "<html><head></head><body>hi</body></html>"
    assert screenshot == b"PNGDATA"


def test_extract_page_cache_without_screenshot() -> None:
    metadata, html, screenshot = extract_page_cache(_make_archive(screenshot=None))

    assert metadata == {"url": "https://example.com"}
    assert html is not None
    assert screenshot is None


def test_extract_page_cache_replaces_invalid_utf8() -> None:
    _, html, _ = extract_page_cache(_make_archive(html=b"<html><body>\xff</body></html>"))

    assert html is not None
    assert "\ufffd" in html


def test_extract_page_cache_invalid_archive_returns_empty() -> None:
    assert extract_page_cache(b"not a tarball") == ({}, None, None)


def test_inject_base_href_into_head() -> None:
    result = inject_base_href("<html><head><title>x</title></head></html>", "https://example.com/p/1")

    assert result.startswith('<html><head><base href="https://example.com/p/1"><title>')


def test_inject_base_href_case_insensitive_head() -> None:
    result = inject_base_href("<HTML><HEAD></HEAD></HTML>", "https://example.com")

    assert '<HEAD><base href="https://example.com">' in result


def test_inject_base_href_before_closing_head() -> None:
    result = inject_base_href("<html><title>x</title></head></html>", "https://example.com")

    assert '<base href="https://example.com"></head>' in result


def test_inject_base_href_without_head() -> None:
    result = inject_base_href("<html><body>x</body></html>", "https://example.com")

    assert result.startswith('<base href="https://example.com"><html>')


def test_inject_base_href_escapes_url() -> None:
    result = inject_base_href("<head></head>", "https://example.com/?a=1&b=2")

    assert 'href="https://example.com/?a=1&amp;b=2"' in result
