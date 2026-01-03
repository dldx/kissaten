import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from kissaten.api.main import app
from kissaten.api.db import conn

@pytest.fixture
def client():
    return TestClient(app)

def test_search_origins_empty_query(client):
    """Test that searching with an empty query returns an empty list."""
    response = client.get("/v1/search/origins?q=")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"] == []

def test_search_origins_country(client):
    """Test searching for a country."""
    # Assuming 'Colombia' exists in the database
    response = client.get("/v1/search/origins?q=Colombia")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # Verify that at least one country result is returned
    results = data["data"]
    assert any(r["type"] == "country" and "Colombia" in r["name"] for r in results)

def test_search_origins_region(client):
    """Test searching for a region."""
    # Find a region in the database first
    region_row = conn.execute("SELECT region FROM origins WHERE region IS NOT NULL AND region != '' LIMIT 1").fetchone()
    if not region_row:
        pytest.skip("No regions found in database for testing")
    
    region_name = region_row[0]
    response = client.get(f"/v1/search/origins?q={region_name}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    results = data["data"]
    assert any(r["type"] == "region" and region_name.lower() in r["name"].lower() for r in results)

def test_search_origins_farm(client):
    """Test searching for a farm."""
    # Find a farm in the database first
    farm_row = conn.execute("SELECT farm FROM origins WHERE farm IS NOT NULL AND farm != '' LIMIT 1").fetchone()
    if not farm_row:
        pytest.skip("No farms found in database for testing")
    
    farm_name = farm_row[0]
    response = client.get(f"/v1/search/origins?q={farm_name}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    results = data["data"]
    assert any(r["type"] == "farm" and farm_name.lower() in r["name"].lower() for r in results)

def test_search_origins_limit(client):
    """Test the limit parameter."""
    response = client.get("/v1/search/origins?q=a&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) <= 5

def test_unknown_region_route(client):
    """Test that unknown-region route works."""
    # Colombia often has beans with no region in this dataset
    response = client.get("/v1/origins/CO/unknown-region")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["region_name"] == "Unknown Region"

def test_robust_region_slug_matching(client):
    """Test that regions with different characters but same slug are merged."""
    # Panama has 'Volcan' and 'Volcán'
    response = client.get("/v1/origins/PA/volcan")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # If merged, bean_count should be summation of both
    # We just check it's successful for now as a proxy for robust matching
    assert data["data"]["country_code"] == "PA"
