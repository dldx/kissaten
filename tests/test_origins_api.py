import os
import sys
from pathlib import Path

# Set environment variable to ensure we're in test mode
os.environ["PYTEST_CURRENT_TEST"] = "test_origins_api.py"

# Add the src directory to the path so we can import kissaten modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from kissaten.api.db import conn, init_database, load_coffee_data
from kissaten.api.main import app


@pytest_asyncio.fixture
async def setup_database():
    """Fixture to initialize database and clean up data before each test"""
    await init_database()

    # Clear existing data
    conn.execute("TRUNCATE TABLE origins")
    conn.execute("TRUNCATE TABLE coffee_beans")
    conn.execute("TRUNCATE TABLE roasters")
    conn.execute("TRUNCATE TABLE country_codes")
    conn.execute("TRUNCATE TABLE processed_files")
    conn.commit()

    yield

    # Cleanup
    conn.execute("TRUNCATE TABLE origins")
    conn.execute("TRUNCATE TABLE coffee_beans")
    conn.execute("TRUNCATE TABLE roasters")
    conn.execute("TRUNCATE TABLE country_codes")
    conn.execute("TRUNCATE TABLE processed_files")
    conn.commit()


@pytest.fixture
def test_data_dir():
    """Fixture to provide test data directory path"""
    test_dir = Path(__file__).parent.parent / "test_data" / "roasters"
    if not test_dir.exists():
        pytest.skip(f"Test data directory not found: {test_dir}")
    return test_dir


@pytest.fixture
def client():
    """Fixture to provide FastAPI test client"""
    return TestClient(app)


@pytest.mark.asyncio
async def test_get_country_detail(setup_database, test_data_dir, client):
    """Test GET /v1/origins/{country_code}"""
    await load_coffee_data(test_data_dir)

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
async def test_get_country_regions(setup_database, test_data_dir, client):
    """Test GET /v1/origins/{country_code}/regions"""
    await load_coffee_data(test_data_dir)

    response = client.get("/v1/origins/ET/regions")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) > 0
    # One of the regions in ET is "Uraga, Guji" based on our manual check
    region_names = [r["region_name"] for r in data["data"]]
    assert any("Guji" in name for name in region_names)


@pytest.mark.asyncio
async def test_get_region_detail(setup_database, test_data_dir, client):
    """Test GET /v1/origins/{country_code}/{region_slug}"""
    await load_coffee_data(test_data_dir)

    # Test valid region with slug (Uraga, Guji -> uraga-guji)
    response = client.get("/v1/origins/ET/uraga-guji")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Uraga" in data["data"]["region_name"]
    assert data["data"]["statistics"]["total_beans"] > 0
    # Verify that we get the full list of farms
    assert len(data["data"]["top_farms"]) > 0
    farm_names = [f["farm_name"] for f in data["data"]["top_farms"]]
    # Just check that we have some string names
    assert all(isinstance(name, str) and len(name) > 0 for name in farm_names)

    # Test case sensitivity/slugification
    response = client.get("/v1/origins/et/URAGA-GUJI")
    assert response.status_code == 200

    # Test non-existent region
    response = client.get("/v1/origins/ET/non-existent-region")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_farm_detail(setup_database, test_data_dir, client):
    """Test GET /v1/origins/{country_code}/{region_slug}/{farm_slug}"""
    await load_coffee_data(test_data_dir)

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
