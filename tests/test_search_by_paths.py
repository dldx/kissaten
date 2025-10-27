"""Test the POST /v1/search/by-paths endpoint."""

import os
import sys
from pathlib import Path

# Set environment variable to ensure we're in test mode
os.environ["PYTEST_CURRENT_TEST"] = "test_search_by_paths.py"

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from kissaten.api.db import conn, init_database, load_coffee_data
from kissaten.api.main import app


@pytest_asyncio.fixture
async def setup_database():
    """Fixture to initialize database and load test data."""
    await init_database()

    # Clear existing data
    conn.execute("DELETE FROM origins")
    conn.execute("DELETE FROM coffee_beans")
    conn.execute("DELETE FROM roasters")
    conn.execute("DELETE FROM country_codes")
    conn.execute("DELETE FROM roaster_location_codes")
    conn.execute("DELETE FROM tasting_notes_categories")
    conn.commit()

    # Load test data
    test_data_dir = Path(__file__).parent.parent / "test_data" / "roasters"
    if test_data_dir.exists():
        await load_coffee_data(test_data_dir)

    yield

    # Cleanup after test
    conn.execute("DELETE FROM origins")
    conn.execute("DELETE FROM coffee_beans")
    conn.execute("DELETE FROM roasters")
    conn.execute("DELETE FROM country_codes")
    conn.execute("DELETE FROM roaster_location_codes")
    conn.execute("DELETE FROM tasting_notes_categories")
    conn.commit()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.mark.asyncio
async def test_search_by_paths_basic(setup_database, client):
    """Test basic search by paths endpoint with real test data."""
    # Test with empty list should fail validation (min_length=1)
    response = client.post(
        "/v1/search/by-paths",
        json={"bean_url_paths": []},
    )
    assert response.status_code == 422  # Validation error

    # Get actual bean_url_paths from the database
    beans_query = """
        SELECT DISTINCT bean_url_path
        FROM coffee_beans
        WHERE bean_url_path IS NOT NULL
        LIMIT 3
    """
    results = conn.execute(beans_query).fetchall()
    bean_paths = [row[0] for row in results if row[0]]

    if not bean_paths:
        pytest.skip("No beans with bean_url_path in test database")

    # Test with valid paths from database
    response = client.post(
        "/v1/search/by-paths",
        json={"bean_url_paths": bean_paths},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == len(bean_paths)
    assert data["metadata"]["total_results"] == len(bean_paths)
    assert data["metadata"]["requested_paths"] == len(bean_paths)

    # Verify returned beans have correct paths
    returned_paths = {bean["bean_url_path"] for bean in data["data"]}
    assert returned_paths == set(bean_paths)


@pytest.mark.asyncio
async def test_search_by_paths_with_real_beans(setup_database, client):
    """Test fetching specific beans with known characteristics."""
    # Get an Ethiopian bean
    ethiopian_query = """
        SELECT DISTINCT cb.bean_url_path, cb.name
        FROM coffee_beans cb
        JOIN origins o ON cb.id = o.bean_id
        WHERE o.country = 'ET' AND cb.bean_url_path IS NOT NULL
        LIMIT 1
    """
    result = conn.execute(ethiopian_query).fetchone()

    if not result:
        pytest.skip("No Ethiopian beans in test database")

    bean_path = result[0]
    bean_name = result[1]

    # Fetch the specific bean
    response = client.post(
        "/v1/search/by-paths",
        json={"bean_url_paths": [bean_path]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 1
    assert data["data"][0]["name"] == bean_name
    assert data["data"][0]["bean_url_path"] == bean_path
    assert len(data["data"][0]["origins"]) > 0
    # Verify at least one origin is from Ethiopia
    assert any(origin["country"] == "ET" for origin in data["data"][0]["origins"])


@pytest.mark.asyncio
async def test_search_by_paths_with_filters(setup_database, client):
    """Test search by paths with additional filter parameters."""
    # Get beans and filter by origin
    all_beans_query = """
        SELECT DISTINCT cb.bean_url_path
        FROM coffee_beans cb
        JOIN origins o ON cb.id = o.bean_id
        WHERE cb.bean_url_path IS NOT NULL
        LIMIT 5
    """
    all_results = conn.execute(all_beans_query).fetchall()
    all_paths = [row[0] for row in all_results if row[0]]

    if not all_paths:
        pytest.skip("No beans in test database")

    # Test with origin filter (only Ethiopian beans)
    response = client.post(
        "/v1/search/by-paths?origin=ET",
        json={"bean_url_paths": all_paths},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # Should return fewer beans than requested (only Ethiopian ones)
    assert len(data["data"]) <= len(all_paths)
    # All returned beans should have at least one Ethiopian origin
    for bean in data["data"]:
        assert any(origin["country"] == "ET" for origin in bean["origins"])


@pytest.mark.asyncio
async def test_search_by_paths_with_in_stock_filter(setup_database, client):
    """Test filtering by stock status."""
    # Get all beans
    all_beans_query = """
        SELECT DISTINCT bean_url_path, in_stock
        FROM coffee_beans
        WHERE bean_url_path IS NOT NULL
        LIMIT 5
    """
    results = conn.execute(all_beans_query).fetchall()
    all_paths = [row[0] for row in results if row[0]]

    if not all_paths:
        pytest.skip("No beans in test database")

    # Test with in_stock_only filter
    response = client.post(
        "/v1/search/by-paths?in_stock_only=true",
        json={"bean_url_paths": all_paths},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # All returned beans should be in stock
    for bean in data["data"]:
        assert bean["in_stock"] is True


@pytest.mark.asyncio
async def test_search_by_paths_currency_conversion(setup_database, client):
    """Test search by paths with currency conversion."""
    # Get a bean with price
    bean_query = """
        SELECT DISTINCT bean_url_path, price, currency
        FROM coffee_beans
        WHERE bean_url_path IS NOT NULL AND price IS NOT NULL
        LIMIT 1
    """
    result = conn.execute(bean_query).fetchone()

    if not result:
        pytest.skip("No beans with prices in test database")

    bean_path, original_price, original_currency = result

    # Test without conversion
    response_no_convert = client.post(
        "/v1/search/by-paths",
        json={"bean_url_paths": [bean_path]},
    )
    assert response_no_convert.status_code == 200
    data_no_convert = response_no_convert.json()
    assert data_no_convert["success"] is True
    assert len(data_no_convert["data"]) == 1
    assert data_no_convert["data"][0]["currency"] == original_currency

    # Test with EUR conversion
    response = client.post(
        "/v1/search/by-paths?convert_to_currency=EUR",
        json={"bean_url_paths": [bean_path]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["metadata"]["currency_conversion"]["enabled"] is True
    assert data["metadata"]["currency_conversion"]["target_currency"] == "EUR"
    assert len(data["data"]) == 1
    bean = data["data"][0]
    assert bean["currency"] == "EUR"
    assert bean["original_currency"] == original_currency
    if original_currency != "EUR":
        assert bean["price_converted"] is True


@pytest.mark.asyncio
async def test_search_by_paths_with_process_filter(setup_database, client):
    """Test filtering by process method."""
    # Get beans with different processes
    process_query = """
        SELECT DISTINCT cb.bean_url_path, o.process
        FROM coffee_beans cb
        JOIN origins o ON cb.id = o.bean_id
        WHERE cb.bean_url_path IS NOT NULL AND o.process IS NOT NULL
        LIMIT 5
    """
    results = conn.execute(process_query).fetchall()

    if not results:
        pytest.skip("No beans with process info in test database")

    all_paths = [row[0] for row in results]

    # Test with natural process filter
    response = client.post(
        "/v1/search/by-paths?process=natural",
        json={"bean_url_paths": all_paths},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    # All returned beans should have natural process in at least one origin
    for bean in data["data"]:
        assert any(
            origin.get("process") and "natural" in origin["process"].lower()
            for origin in bean["origins"]
        )


@pytest.mark.asyncio
async def test_search_by_paths_nonexistent_paths(setup_database, client):
    """Test with paths that don't exist in database."""
    response = client.post(
        "/v1/search/by-paths",
        json={"bean_url_paths": ["/nonexistent/bean1", "/fake/bean2"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 0  # No beans found
    assert data["metadata"]["total_results"] == 0
    assert data["metadata"]["requested_paths"] == 2


def test_search_by_paths_max_limit(client):
    """Test that max_length validation works (100 paths maximum)."""
    # Generate 101 paths (exceeds max_length=100)
    too_many_paths = [f"/test/path{i}" for i in range(101)]

    response = client.post(
        "/v1/search/by-paths",
        json={"bean_url_paths": too_many_paths},
    )
    assert response.status_code == 422  # Validation error

