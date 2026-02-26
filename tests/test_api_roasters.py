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
