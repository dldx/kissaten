import pytest
from fastapi.testclient import TestClient

from kissaten.api.db import conn
from kissaten.api.main import app


@pytest.mark.asyncio
async def test_get_country_detail(client):
    """Test GET /v1/origins/{country_code}"""

    # Test valid country (Ethiopia)
    response = client.get("/v1/origins/ET")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["country_code"] == "ET"
    # Country name might be ET if not in country_codes table, or the full name if it is.
    # In search_coffee_beans.py tests, they often check for existence of data.
    assert data["data"]["statistics"]["total_beans"] > 0
    assert len(data["data"]["top_regions"]) > 0

    # Test invalid country
    response = client.get("/v1/origins/XX")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_country_regions(client):
    """Test GET /v1/origins/{country_code}/regions"""

    response = client.get("/v1/origins/ET/regions")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) > 0
    # ET has been geocoded, so "Uraga" and "Uraga, Guji" are merged under
    # the canonical state "Oromiya".
    region_names = [r["region_name"] for r in data["data"]]
    assert any("Oromiya" in name for name in region_names)


@pytest.mark.asyncio
async def test_get_region_detail(client):
    """Test GET /v1/origins/{country_code}/{region_slug}"""

    # Test valid canonical region (Uraga, Guji → geocoded → "Oromiya")
    response = client.get("/v1/origins/ET/oromiya")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Oromiya" in data["data"]["region_name"]
    assert data["data"]["statistics"]["total_beans"] > 0
    # Verify that we get the full list of farms
    assert len(data["data"]["top_farms"]) > 0
    farm_names = [f["farm_name"] for f in data["data"]["top_farms"]]
    # Just check that we have some string names
    assert all(isinstance(name, str) and len(name) > 0 for name in farm_names)

    # Test case sensitivity/slugification
    response = client.get("/v1/origins/et/OROMIYA")
    assert response.status_code == 200

    # Test non-existent region
    response = client.get("/v1/origins/ET/non-existent-region")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_origins_sitemap_entries(client):
    """Test GET /v1/origins/sitemap-entries (bulk sitemap source)."""

    response = client.get("/v1/origins/sitemap-entries")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    entries = data["data"]
    assert len(entries) > 0

    # The static path must not be swallowed by /v1/origins/{country_code}.
    assert all(e["country_code"] != "sitemap-entries" for e in entries)

    regions = [e for e in entries if e["farm_name"] is None]
    farms = [e for e in entries if e["farm_name"] is not None]
    assert len(regions) > 0
    assert len(farms) > 0

    for e in entries:
        assert set(e.keys()) == {"country_code", "region_name", "farm_name"}
        assert e["country_code"]
        assert e["region_name"]

    # Every farm row belongs to a region row.
    region_keys = {(e["country_code"], e["region_name"]) for e in regions}
    for e in farms:
        assert (e["country_code"], e["region_name"]) in region_keys

    # Bulk region names must match the per-country regions list exactly.
    cc = regions[0]["country_code"]
    listed = {
        r["region_name"]
        for r in client.get(f"/v1/origins/{cc}/regions").json()["data"]
    }
    bulk = {e["region_name"] for e in regions if e["country_code"] == cc}
    assert bulk == listed


@pytest.mark.asyncio
async def test_get_farm_detail(client):
    """Test GET /v1/origins/{country_code}/{region_slug}/{farm_slug}"""

    # Test valid farm
    response = client.get("/v1/origins/CR/west-valley/finca-sumava")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["farm_name"] == "Finca Sumava"
    assert len(data["data"]["beans"]) > 0

    # Test invalid farm
    response = client.get("/v1/origins/CR/west-valley/non-existent-farm")
    assert response.status_code == 404
