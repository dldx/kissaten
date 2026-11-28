"""API tests for the admin page-cache viewer."""

import io
import json
import tarfile

import pytest

from kissaten.api.db import conn
from kissaten.cache.page_cache import page_cache_filename
from kissaten.cache.r2_page_cache import reset_r2_caches

_ADMIN_TOKEN = "test-admin-token"
_ADMIN_HEADER = "X-Kissaten-Admin-Token"

_BEAN_ID = 91000001
_ROASTER = "ZZ Cache Viewer Roaster"
_ROASTER_DIR = "zz_cache_viewer_roaster"
_BEAN_SLUG = "test-bean"
_BEAN_URL = "https://cache-viewer.example.com/products/test-bean"
_BEAN_URL_PATH = f"/{_ROASTER_DIR}/{_BEAN_SLUG}"
_SESSION = "20240101"
_FILENAME = page_cache_filename(_BEAN_URL)
_HTML = "<html><head><title>bean</title></head><body>cached</body></html>"
_SCREENSHOT = b"\x89PNG\r\n\x1a\nfake-png-bytes"
_METADATA = {"url": _BEAN_URL, "cached_at": "2024-01-01T00:00:00+00:00", "has_screenshot": True}


def _make_archive() -> bytes:
    entries: list[tuple[str, bytes]] = [
        ("metadata.json", json.dumps(_METADATA).encode("utf-8")),
        ("page.html", _HTML.encode("utf-8")),
        ("screenshot.png", _SCREENSHOT),
    ]
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, data in entries:
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


@pytest.fixture
def cache_viewer_env(tmp_path, client, monkeypatch):
    """Point the viewer at a synthetic cache and insert a matching bean row."""
    cache_root = tmp_path / "cache"
    session_dir = cache_root / "roasters" / _ROASTER_DIR / _SESSION
    session_dir.mkdir(parents=True)
    archive = _make_archive()
    (session_dir / _FILENAME).write_bytes(archive)

    monkeypatch.setenv("KISSATEN_CACHE_DIR", str(cache_root))
    # Ensure local-only mode: no R2 configuration at all.
    for var in (
        "KISSATEN_R2_ENDPOINT",
        "KISSATEN_R2_BUCKET",
        "KISSATEN_R2_PREFIX",
        "KISSATEN_R2_ACCESS_KEY_ID",
        "KISSATEN_R2_SECRET_ACCESS_KEY",
        "KISSATEN_R2_LIST_CACHE_TTL",
    ):
        monkeypatch.delenv(var, raising=False)
    reset_r2_caches()

    for var in ("KISSATEN_ADMIN_API_TOKEN",):
        monkeypatch.delenv(var, raising=False)

    conn.execute(
        """
        INSERT INTO coffee_beans
            (id, name, roaster, url, is_single_origin, is_tasting_kit,
             requires_review, in_stock, scraper_version, clean_url_slug,
             bean_url_path, scraped_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)
        """,
        [
            _BEAN_ID,
            "ZZ Cache Viewer Bean",
            _ROASTER,
            _BEAN_URL,
            True,
            False,
            False,
            True,
            "2.0",
            _BEAN_SLUG,
            _BEAN_URL_PATH,
        ],
    )
    conn.commit()

    yield {"archive": archive}

    conn.execute("DELETE FROM coffee_beans WHERE id = ?", [_BEAN_ID])
    conn.commit()
    reset_r2_caches()


def _auth(monkeypatch, token: str = _ADMIN_TOKEN) -> dict[str, str]:
    monkeypatch.setenv("KISSATEN_ADMIN_API_TOKEN", token)
    return {_ADMIN_HEADER: token}


def _list_url() -> str:
    return f"/v1/admin/cache/beans/{_ROASTER_DIR}/{_BEAN_SLUG}"


def _content_url() -> str:
    return f"/v1/admin/cache/beans/{_ROASTER_DIR}/{_BEAN_SLUG}/content"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_missing_token_returns_401(cache_viewer_env, client, monkeypatch):
    monkeypatch.setenv("KISSATEN_ADMIN_API_TOKEN", _ADMIN_TOKEN)

    response = client.get(_list_url())

    assert response.status_code == 401


def test_wrong_token_returns_401(cache_viewer_env, client, monkeypatch):
    monkeypatch.setenv("KISSATEN_ADMIN_API_TOKEN", _ADMIN_TOKEN)

    response = client.get(_list_url(), headers={_ADMIN_HEADER: "wrong-token"})

    assert response.status_code == 401


def test_unset_env_returns_503(cache_viewer_env, client, monkeypatch):
    monkeypatch.delenv("KISSATEN_ADMIN_API_TOKEN", raising=False)

    response = client.get(_list_url(), headers={_ADMIN_HEADER: _ADMIN_TOKEN})

    assert response.status_code == 503


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


def test_list_returns_local_snapshot(cache_viewer_env, client, monkeypatch):
    headers = _auth(monkeypatch)

    response = client.get(_list_url(), headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True

    data = body["data"]
    assert data["bean"]["name"] == "ZZ Cache Viewer Bean"
    assert data["bean"]["roaster"] == _ROASTER
    assert data["bean"]["url"] == _BEAN_URL
    assert data["bean"]["bean_url_path"] == _BEAN_URL_PATH
    assert data["bean"]["scraped_at"] is not None

    assert _ROASTER_DIR in data["roaster_dirs"]
    assert data["storage"] == {"local": True, "r2": False}

    assert len(data["snapshots"]) == 1
    snapshot = data["snapshots"][0]
    assert snapshot["session_date"] == _SESSION
    assert snapshot["filename"] == _FILENAME
    assert snapshot["source"] == "local"
    assert snapshot["size"] == len(cache_viewer_env["archive"])
    assert snapshot["last_modified"] is not None


def test_list_unknown_bean_returns_404(cache_viewer_env, client, monkeypatch):
    headers = _auth(monkeypatch)

    response = client.get("/v1/admin/cache/beans/no-such-roaster/no-such-bean", headers=headers)

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------


def test_html_content_has_security_headers_and_base_href(cache_viewer_env, client, monkeypatch):
    headers = _auth(monkeypatch)

    response = client.get(
        _content_url(),
        params={"session": _SESSION, "filename": _FILENAME, "kind": "html"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "sandbox" in response.headers["content-security-policy"]
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "private, no-store"

    assert f'<base href="{_BEAN_URL}">' in response.text
    assert "cached" in response.text


def test_screenshot_content(cache_viewer_env, client, monkeypatch):
    headers = _auth(monkeypatch)

    response = client.get(
        _content_url(),
        params={"session": _SESSION, "filename": _FILENAME, "kind": "screenshot"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    assert response.content == _SCREENSHOT


def test_metadata_content(cache_viewer_env, client, monkeypatch):
    headers = _auth(monkeypatch)

    response = client.get(
        _content_url(),
        params={"session": _SESSION, "filename": _FILENAME, "kind": "metadata"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == _METADATA


def test_raw_content(cache_viewer_env, client, monkeypatch):
    headers = _auth(monkeypatch)

    response = client.get(
        _content_url(),
        params={"session": _SESSION, "filename": _FILENAME, "kind": "raw"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/gzip")
    assert f'filename="{_FILENAME}"' in response.headers["content-disposition"]
    assert response.content == cache_viewer_env["archive"]


def test_unknown_session_returns_404(cache_viewer_env, client, monkeypatch):
    headers = _auth(monkeypatch)

    response = client.get(
        _content_url(),
        params={"session": "19990101", "filename": _FILENAME, "kind": "html"},
        headers=headers,
    )

    assert response.status_code == 404


def test_unknown_filename_returns_404(cache_viewer_env, client, monkeypatch):
    headers = _auth(monkeypatch)

    response = client.get(
        _content_url(),
        params={"session": _SESSION, "filename": "other.tar.gz", "kind": "html"},
        headers=headers,
    )

    assert response.status_code == 404


def test_invalid_session_returns_400(cache_viewer_env, client, monkeypatch):
    headers = _auth(monkeypatch)

    response = client.get(
        _content_url(),
        params={"session": "2024-01-01", "filename": _FILENAME, "kind": "html"},
        headers=headers,
    )

    assert response.status_code == 400


def test_invalid_filename_returns_400(cache_viewer_env, client, monkeypatch):
    headers = _auth(monkeypatch)

    response = client.get(
        _content_url(),
        params={"session": _SESSION, "filename": "../evil.tar.gz", "kind": "html"},
        headers=headers,
    )

    assert response.status_code == 400


def test_content_unknown_bean_returns_404(cache_viewer_env, client, monkeypatch):
    headers = _auth(monkeypatch)

    response = client.get(
        "/v1/admin/cache/beans/no-such-roaster/no-such-bean/content",
        params={"session": _SESSION, "filename": _FILENAME, "kind": "html"},
        headers=headers,
    )

    assert response.status_code == 404
