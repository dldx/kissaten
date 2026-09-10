"""
Tests for roaster and bean detail API endpoints.

Covers:
- GET /v1/roasters
- GET /v1/beans/{roaster_slug}/{bean_slug}
- GET /v1/beans/{roaster_slug}/{bean_slug}/recommendations
"""

import pytest


@pytest.mark.asyncio
async def test_get_roasters_returns_list(client):
    """GET /v1/roasters should return a list of roasters."""
    response = client.get("/v1/roasters")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_get_roasters_contains_expected_fields(client):
    """Each roaster entry should have the required fields."""
    response = client.get("/v1/roasters")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) > 0, "Expected at least one roaster in the database"
    roaster = data["data"][0]
    for field in ("id", "name", "slug", "website", "active", "current_beans_count", "location_codes"):
        assert field in roaster, f"Field '{field}' missing from roaster response"


@pytest.mark.asyncio
async def test_get_roasters_metadata(client):
    """GET /v1/roasters should include metadata with total_roasters."""
    response = client.get("/v1/roasters")
    assert response.status_code == 200
    data = response.json()
    assert "metadata" in data
    assert "total_roasters" in data["metadata"]
    assert data["metadata"]["total_roasters"] == len(data["data"])


@pytest.mark.asyncio
async def test_get_roasters_location_codes_is_list(client):
    """location_codes field should be a list for every roaster."""
    response = client.get("/v1/roasters")
    assert response.status_code == 200
    for roaster in response.json()["data"]:
        assert isinstance(roaster["location_codes"], list), (
            f"location_codes should be a list for roaster '{roaster['name']}'"
        )


@pytest.mark.asyncio
async def test_get_bean_by_slug_valid(client):
    """GET /v1/beans/{roaster_slug}/{bean_slug} should return 200 for a valid bean."""
    # Discover a real bean_url_path from the roasters listing
    from kissaten.api.db import conn

    row = conn.execute(
        "SELECT bean_url_path FROM coffee_beans WHERE bean_url_path IS NOT NULL LIMIT 1"
    ).fetchone()
    if not row:
        pytest.skip("No beans with bean_url_path found in test database")

    response = client.get(f"/v1/beans{row[0]}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data


@pytest.mark.asyncio
async def test_get_bean_by_slug_invalid_returns_404(client):
    """GET /v1/beans/{roaster_slug}/{bean_slug} should return 404 for unknown beans."""
    response = client.get("/v1/beans/nonexistent-roaster/nonexistent-bean")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_bean_recommendations_valid(client):
    """GET /v1/beans/{roaster_slug}/{bean_slug}/recommendations should return 200."""
    from kissaten.api.db import conn

    row = conn.execute(
        "SELECT bean_url_path FROM coffee_beans WHERE bean_url_path IS NOT NULL LIMIT 1"
    ).fetchone()
    if not row:
        pytest.skip("No beans with bean_url_path found in test database")

    response = client.get(f"/v1/beans{row[0]}/recommendations")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_get_bean_recommendations_invalid_returns_404(client):
    """GET /v1/beans/{roaster_slug}/{bean_slug}/recommendations returns 404 for unknown beans."""
    response = client.get("/v1/beans/nonexistent-roaster/nonexistent-bean/recommendations")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_bean_recommendations_origin_filter_constrains_results(client):
    """Passing origin=<code> as a hard constraint: every result carries that origin."""
    from kissaten.api.db import conn

    bean_path = conn.execute(
        """
        SELECT cb.bean_url_path FROM coffee_beans cb
        JOIN origins o ON o.bean_id = cb.id
        WHERE o.country = 'KE' AND cb.bean_url_path IS NOT NULL
        LIMIT 1
        """
    ).fetchone()
    if not bean_path:
        pytest.skip("No Kenyan bean in test database")

    response = client.get(f"/v1/beans{bean_path[0]}/recommendations", params={"origin": "KE"})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["metadata"]["user_filters"] == {"origin": ["KE"]}
    for rec in data["data"]:
        rec_countries = {o["country"] for o in rec.get("origins", [])}
        assert "KE" in rec_countries, f"{rec.get('bean_url_path')} lacks KE origin: {rec_countries}"


@pytest.mark.asyncio
async def test_get_bean_recommendations_user_filter_overrides_bean_anchor(client):
    """A user origin filter replaces the bean-derived origin anchor entirely.

    The seed bean is Ethiopian; constraining to Kenya must still yield only
    Kenyan candidates (i.e. the bean's own origin must not leak into results).
    """
    from kissaten.api.db import conn

    bean_path = conn.execute(
        """
        SELECT cb.bean_url_path FROM coffee_beans cb
        JOIN origins o ON o.bean_id = cb.id
        WHERE o.country = 'ET' AND cb.bean_url_path IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM origins o2 WHERE o2.bean_id = cb.id AND o2.country = 'KE')
        LIMIT 1
        """
    ).fetchone()
    if not bean_path:
        pytest.skip("No Ethiopian-only bean in test database")

    response = client.get(f"/v1/beans{bean_path[0]}/recommendations", params={"origin": "KE"})
    assert response.status_code == 200
    for rec in response.json()["data"]:
        rec_countries = {o["country"] for o in rec.get("origins", [])}
        assert "KE" in rec_countries, f"{rec.get('bean_url_path')} lacks KE origin: {rec_countries}"
        assert "ET" not in rec_countries or len(rec_countries) > 1  # ET alone would mean the anchor leaked


@pytest.mark.asyncio
async def test_get_bean_recommendations_budget_constraint_in_currency(client):
    """max_price + convert_to_currency is a hard constraint on converted (USD) prices.

    Display conversion is separate (and needs FX rates); the constraint itself
    compares cb.price_usd, so a tiny max_price must eliminate every candidate.
    """
    from kissaten.api.db import conn

    bean_path = conn.execute(
        "SELECT bean_url_path FROM coffee_beans WHERE bean_url_path IS NOT NULL LIMIT 1"
    ).fetchone()
    if not bean_path:
        pytest.skip("No beans with bean_url_path found in test database")

    url = f"/v1/beans{bean_path[0]}/recommendations"
    generous = client.get(url, params={"max_price": "100000", "convert_to_currency": "USD"})
    assert generous.status_code == 200
    assert len(generous.json()["data"]) > 0
    assert generous.json()["metadata"]["user_filters"] == {
        "max_price": 100000.0,
        "convert_to_currency": "USD",
    }

    tiny = client.get(url, params={"max_price": "0.01", "convert_to_currency": "USD"})
    assert tiny.status_code == 200
    assert tiny.json()["data"] == []


@pytest.mark.asyncio
async def test_get_bean_recommendations_bean_anchor_used_when_no_filter(client):
    """Without user filters, bean-derived similarity anchors still apply (unchanged behavior)."""
    from kissaten.api.db import conn

    bean_path = conn.execute(
        "SELECT bean_url_path FROM coffee_beans WHERE bean_url_path IS NOT NULL LIMIT 1"
    ).fetchone()
    if not bean_path:
        pytest.skip("No beans with bean_url_path found in test database")

    response = client.get(f"/v1/beans{bean_path[0]}/recommendations")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "user_filters" not in body["metadata"] or body["metadata"]["user_filters"] is None
