"""API tests for the tasting-kit review flags (requires_review / is_tasting_kit).

Public search hides rows with ``requires_review=true`` unless
``include_unreviewed=true`` is passed (admin). ``is_tasting_kit`` is always a
hard filter. This follows the conftest-based pattern of
``test_search_coffee_beans.py`` (session ``client`` fixture) and inserts a
flagged bean directly into the session test DB.
"""

import pytest

from kissaten.api.db import conn

# Unique names so the test beans never collide with the shared test dataset.
_FLAGGED_NAME = "ZZ_TASTING_KIT_TEST_FLAGGED"
_NORMAL_NAME = "ZZ_TASTING_KIT_TEST_NORMAL"
_PREFIX = "ZZ_TASTING_KIT_TEST_"

_FLAGGED_URL = "https://proper-roaster.example.com/products/test-taster-pack"
_NORMAL_URL = "https://proper-roaster.example.com/products/test-yirgacheffe"


def _names(beans):
    return {b["name"] for b in beans}


@pytest.fixture
def review_flags(client):
    """Insert one flagged (kit + requires_review) bean and one normal bean.

    Relies on the session ``client`` fixture having already loaded the schema
    and test dataset. Cleaned up after each test so other session tests are
    unaffected.
    """
    rows = [
        (
            90000001,
            _FLAGGED_NAME,
            "Proper Roaster",
            _FLAGGED_URL,
            True,  # is_single_origin
            True,  # is_tasting_kit
            True,  # requires_review
            True,  # in_stock
            "2.0",  # scraper_version
            "zz-tasting-kit-test-flagged",
        ),
        (
            90000002,
            _NORMAL_NAME,
            "Proper Roaster",
            _NORMAL_URL,
            True,  # is_single_origin
            False,  # is_tasting_kit
            False,  # requires_review
            True,  # in_stock
            "2.0",  # scraper_version
            "zz-tasting-kit-test-normal",
        ),
    ]
    conn.executemany(
        """
        INSERT INTO coffee_beans
            (id, name, roaster, url, is_single_origin, is_tasting_kit,
             requires_review, in_stock, scraper_version, clean_url_slug,
             scraped_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)
        """,
        rows,
    )
    conn.commit()
    yield
    conn.execute("DELETE FROM coffee_beans WHERE url IN (?, ?)", (_FLAGGED_URL, _NORMAL_URL))
    conn.commit()


@pytest.mark.asyncio
async def test_flagged_bean_hidden_by_default(review_flags, client):
    response = client.get("/v1/search?per_page=100")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    names = _names(data["data"])
    assert _NORMAL_NAME in names
    # Without include_unreviewed, requires_review=true beans are hidden.
    assert _FLAGGED_NAME not in names


@pytest.mark.asyncio
async def test_flagged_bean_shown_with_include_unreviewed(review_flags, client):
    response = client.get("/v1/search?per_page=100&include_unreviewed=true")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    names = _names(data["data"])
    assert _NORMAL_NAME in names
    assert _FLAGGED_NAME in names


@pytest.mark.asyncio
async def test_is_tasting_kit_hard_filter(review_flags, client):
    response = client.get("/v1/search?per_page=100&is_tasting_kit=true&include_unreviewed=true")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    names = _names(data["data"])
    assert _FLAGGED_NAME in names
    assert _NORMAL_NAME not in names

    # Every returned row carries is_tasting_kit=true.
    for bean in data["data"]:
        assert bean.get("is_tasting_kit") is True


@pytest.mark.asyncio
async def test_unflagged_search_still_returns_others(review_flags, client):
    # Sanity: the normal bean is visible in the default public view.
    response = client.get("/v1/search?per_page=100")
    data = response.json()
    assert _NORMAL_NAME in _names(data["data"])
    assert data["pagination"]["total_items"] > 0


@pytest.mark.asyncio
async def test_requires_review_filter_returns_only_flagged(review_flags, client):
    """requires_review=true returns ONLY the flagged bean, not the normal one."""
    response = client.get("/v1/search?per_page=100&requires_review=true")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    names = _names(data["data"])
    assert _FLAGGED_NAME in names
    assert _NORMAL_NAME not in names

    # Every returned row carries requires_review=true (no flood of the catalogue).
    for bean in data["data"]:
        assert bean.get("requires_review") is True


@pytest.mark.asyncio
async def test_requires_review_filter_false_returns_unflagged(review_flags, client):
    """requires_review=false returns only beans that do NOT need review."""
    response = client.get("/v1/search?per_page=100&requires_review=false")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    names = _names(data["data"])
    assert _NORMAL_NAME in names
    assert _FLAGGED_NAME not in names
