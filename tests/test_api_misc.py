"""
Tests for miscellaneous API endpoints.

Covers:
- GET /
- GET /health
- GET /v1/health
- GET /v1/stats
- GET /v1/processes
- GET /v1/processes/{process_slug}
- GET /v1/varietals
- GET /v1/varietals/{varietal_slug}
- GET /v1/currencies
- GET /v1/convert
"""

import pytest


# ---------------------------------------------------------------------------
# Root & health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_root_returns_200(client):
    """GET / should respond successfully."""
    response = client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_check(client):
    """GET /health should return healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_v1_health_check(client):
    """GET /v1/health should return healthy status."""
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_stats_returns_success(client):
    """GET /v1/stats should return a successful response."""
    response = client.get("/v1/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data


@pytest.mark.asyncio
async def test_get_stats_contains_bean_count(client):
    """GET /v1/stats data should include bean count information."""
    response = client.get("/v1/stats")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "total_beans" in data or "beans" in str(data).lower()


# ---------------------------------------------------------------------------
# Processes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_processes_returns_success(client):
    """GET /v1/processes should return a successful response."""
    response = client.get("/v1/processes")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data


@pytest.mark.asyncio
async def test_get_processes_data_is_dict(client):
    """GET /v1/processes data should be a dict (grouped by category)."""
    response = client.get("/v1/processes")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["data"], dict)


@pytest.mark.asyncio
async def test_get_process_by_slug_valid(client):
    """GET /v1/processes/{process_slug} should return 200 for a known process."""
    processes_response = client.get("/v1/processes")
    assert processes_response.status_code == 200
    processes_data = processes_response.json()["data"]

    # Find a valid slug from the data
    slug = None
    for _category, entries in processes_data.items():
        if isinstance(entries, list) and entries:
            slug = entries[0].get("slug")
            if slug:
                break
        elif isinstance(entries, dict):
            processes = entries.get("processes", [])
            if processes:
                slug = processes[0].get("slug")
                if slug:
                    break

    if not slug:
        pytest.skip("No process slugs found in /v1/processes response")

    response = client.get(f"/v1/processes/{slug}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_process_by_slug_invalid_returns_404(client):
    """GET /v1/processes/{process_slug} should return 404 for unknown process."""
    response = client.get("/v1/processes/totally-unknown-process-xyz")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Varietals
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_varietals_returns_success(client):
    """GET /v1/varietals should return a successful response."""
    response = client.get("/v1/varietals")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data


@pytest.mark.asyncio
async def test_get_varietals_data_is_dict(client):
    """GET /v1/varietals data should be a dict (grouped by category)."""
    response = client.get("/v1/varietals")
    assert response.status_code == 200
    assert isinstance(response.json()["data"], dict)


@pytest.mark.asyncio
async def test_get_varietal_by_slug_valid(client):
    """GET /v1/varietals/{varietal_slug} should return 200 for a known varietal."""
    varietals_response = client.get("/v1/varietals")
    assert varietals_response.status_code == 200
    varietals_data = varietals_response.json()["data"]

    slug = None
    for _category, category_data in varietals_data.items():
        varietals = category_data.get("varietals", [])
        if varietals:
            slug = varietals[0].get("slug")
            if slug:
                break

    if not slug:
        pytest.skip("No varietal slugs found in /v1/varietals response")

    response = client.get(f"/v1/varietals/{slug}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_get_varietal_by_slug_invalid_returns_404(client):
    """GET /v1/varietals/{varietal_slug} should return 404 for unknown varietal."""
    response = client.get("/v1/varietals/nonexistent-varietal-xyz")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Currency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_currencies_returns_200(client):
    """GET /v1/currencies should return HTTP 200."""
    response = client.get("/v1/currencies")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_currencies_response_shape(client):
    """GET /v1/currencies should return a success response with a list of currencies."""
    response = client.get("/v1/currencies")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_convert_currency_valid(client):
    """GET /v1/convert should convert a known amount between currencies."""
    # Skip if no exchange rates available
    currencies_response = client.get("/v1/currencies")
    currencies = currencies_response.json().get("data", [])
    if not currencies:
        pytest.skip("No currency rates available in test database")

    target = currencies[0]["code"]
    response = client.get(f"/v1/convert?amount=10&from_currency=USD&to_currency={target}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    result = data["data"]
    assert result["original_amount"] == 10.0
    assert result["from_currency"] == "USD"
    assert result["to_currency"] == target
    assert "converted_amount" in result


@pytest.mark.asyncio
async def test_convert_currency_unknown_currency_returns_error(client):
    """GET /v1/convert with an unknown currency should return an error response."""
    response = client.get("/v1/convert?amount=5&from_currency=USD&to_currency=UNKNOWN")
    # Either 400 (bad request) or 500 (db error) are acceptable
    assert response.status_code in (400, 500)
