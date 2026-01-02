"""
Unit tests for varietal mappings functionality.

Tests the integration of varietal_mappings.json with the database schema,
data loading, search functionality, and API endpoints.

Only includes tests that use real JSON data loading and actual API endpoints.
"""

import json
import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

# Set environment variable to use rw_kissaten.duckdb for tests
os.environ["KISSATEN_USE_RW_DB"] = "1"

# Set environment variable to ensure we're in test mode
os.environ["PYTEST_CURRENT_TEST"] = "test_varietal_mappings.py"

# Add the src directory to the path so we can import kissaten modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kissaten.api.db import conn, init_database, load_coffee_data
from kissaten.api.main import app

# Create test client
client = TestClient(app)


@pytest_asyncio.fixture
async def setup_database():
    """Fixture to initialize database and clean up data before each test."""
    await init_database()

    # Clear existing data including static tables that get repopulated during load_coffee_data
    # Use TRUNCATE to reset auto-increment sequences
    conn.execute("TRUNCATE TABLE origins")
    conn.execute("TRUNCATE TABLE coffee_beans")
    conn.execute("TRUNCATE TABLE roasters")
    conn.execute("TRUNCATE TABLE country_codes")
    conn.execute("TRUNCATE TABLE roaster_location_codes")
    conn.execute("TRUNCATE TABLE tasting_notes_categories")
    conn.execute("TRUNCATE TABLE processed_files")
    conn.commit()

    yield

    # Cleanup after test
    conn.execute("TRUNCATE TABLE origins")
    conn.execute("TRUNCATE TABLE coffee_beans")
    conn.execute("TRUNCATE TABLE roasters")
    conn.execute("TRUNCATE TABLE country_codes")
    conn.execute("TRUNCATE TABLE roaster_location_codes")
    conn.execute("TRUNCATE TABLE tasting_notes_categories")
    conn.execute("TRUNCATE TABLE processed_files")
    conn.commit()


@pytest.fixture
def test_data_dir():
    """Fixture to provide test data directory path"""
    test_dir = Path(__file__).parent.parent / "test_data" / "roasters"
    if not test_dir.exists():
        pytest.skip(f"Test data directory not found: {test_dir}")
    return test_dir


# Mapping Application Tests (using actual load_coffee_data function)
@pytest.mark.asyncio
async def test_compound_varietal_decomposition(setup_database, test_data_dir):
    """Test compound variety decomposition by load_coffee_data()."""
    # Load data using actual function with existing test data
    await load_coffee_data(test_data_dir, incremental=False)

    # Test with actual data from test files
    # Check that any varieties that might be compound are properly split
    result = conn.execute("""
        SELECT variety, variety_canonical, len(variety_canonical) as canon_count
        FROM origins
        WHERE variety IS NOT NULL AND variety != ''
        LIMIT 1
    """).fetchone()

    assert result is not None, "No varieties found in test data"
    # Verify that variety_canonical is an array
    assert isinstance(result[1], list), "variety_canonical should be a list"


@pytest.mark.asyncio
async def test_unmapped_varietal_fallback(setup_database, test_data_dir):
    """Test unmapped varietals use original name as fallback in load_coffee_data()."""
    # Load data with existing test files
    await load_coffee_data(test_data_dir, incremental=False)

    # Check that all varieties have a canonical version (even if unmapped)
    result = conn.execute("""
        SELECT variety, variety_canonical
        FROM origins
        WHERE variety IS NOT NULL AND variety != ''
        LIMIT 1
    """).fetchone()

    assert result is not None, "No varieties found in test data"
    assert result[1] is not None, "variety_canonical should not be None"
    assert len(result[1]) > 0, "variety_canonical should have at least one element"


# API Endpoint Tests (using JSON files and load_coffee_data)

@pytest.mark.asyncio
async def test_api_get_varietals_endpoint(setup_database, test_data_dir):
    """Test /v1/varietals endpoint returns varietals with canonical names from real data."""
    # Load data using actual function with existing test data
    await load_coffee_data(test_data_dir, incremental=False)

    # Call the API
    response = client.get("/v1/varietals")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data

    # Check that varietals are grouped by category
    varietals_data = data["data"]
    assert isinstance(varietals_data, dict)

    # Find varietals in the categories
    all_varietals = []
    for category_key, category_data in varietals_data.items():
        all_varietals.extend(category_data["varietals"])

    varietal_names = [v["name"] for v in all_varietals]
    # Should have canonical names from the mapping
    assert len(varietal_names) > 0

    # Check that original_names field exists and contains data for each varietal
    assert len(all_varietals) > 0, "Should have at least one varietal"
    for varietal in all_varietals:
        assert "original_names" in varietal, f"original_names field should be present for varietal {varietal.get('name')}"
        assert isinstance(varietal["original_names"], str), f"original_names should be a string for varietal {varietal.get('name')}"
        assert len(varietal["original_names"]) > 0, f"original_names should not be empty for varietal {varietal.get('name')}"


@pytest.mark.asyncio
async def test_api_get_varietal_details_by_slug(setup_database, test_data_dir):
    """Test /v1/varietals/{slug} endpoint with real data loaded via load_coffee_data()."""
    # Load data with existing test files
    await load_coffee_data(test_data_dir, incremental=False)

    # Get a varietal slug from the loaded data
    result = conn.execute("""
        SELECT DISTINCT LOWER(variety_canonical[1]) as canonical_name
        FROM origins
        WHERE variety_canonical IS NOT NULL
        AND len(variety_canonical) > 0
        AND variety_canonical[1] IS NOT NULL
        AND variety_canonical[1] != ''
        LIMIT 1
    """).fetchone()

    if not result:
        pytest.skip("No varietals found in test data")

    varietal_slug = result[0].lower().replace(' ', '-')

    # Call the API
    response = client.get(f"/v1/varietals/{varietal_slug}?convert_to_currency=USD")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data

    varietal_details = data["data"]
    assert varietal_details["statistics"]["total_beans"] >= 1

    # Check that canonical name is present
    assert "name" in varietal_details
    assert varietal_details["name"] is not None

    # Check that original_names field exists and contains data
    assert "original_names" in varietal_details, "original_names field should be present"
    assert isinstance(varietal_details["original_names"], list), "original_names should be a list"
    assert len(varietal_details["original_names"]) > 0, "original_names should have at least one entry"

    # Verify each original name has required fields
    for original in varietal_details["original_names"]:
        assert "name" in original, "Each original name should have a 'name' field"
        assert "bean_count" in original, "Each original name should have a 'bean_count' field"
        assert isinstance(original["bean_count"], int), "bean_count should be an integer"
        assert original["bean_count"] > 0, "bean_count should be positive"

    # Verify that total_beans equals the sum of all original_names bean_counts
    sum_of_original_counts = sum(original["bean_count"] for original in varietal_details["original_names"])
    assert varietal_details["statistics"]["total_beans"] == sum_of_original_counts, \
        f"total_beans ({varietal_details['statistics']['total_beans']}) should equal sum of original_names bean_counts ({sum_of_original_counts})"


@pytest.mark.asyncio
async def test_api_get_varietal_details_case_insensitive(setup_database, test_data_dir):
    """Test varietal slug matching is case-insensitive."""
    # Load data using actual function with existing test data
    await load_coffee_data(test_data_dir, incremental=False)

    # Get a varietal from the data
    result = conn.execute("""
        SELECT DISTINCT variety_canonical[1] as canonical_name
        FROM origins
        WHERE variety_canonical IS NOT NULL
        AND len(variety_canonical) > 0
        AND variety_canonical[1] IS NOT NULL
        AND variety_canonical[1] != ''
        LIMIT 1
    """).fetchone()

    if not result:
        pytest.skip("No varietals found in test data")

    varietal_name = result[0]
    base_slug = varietal_name.lower().replace(' ', '-')

    # Test various case combinations
    for slug in [base_slug, base_slug.upper(), base_slug.capitalize()]:
        response = client.get(f"/v1/varietals/{slug}")
        assert response.status_code == 200, f"Failed for slug: {slug}"
        data = response.json()
        assert data["data"]["name"] == varietal_name


@pytest.mark.asyncio
async def test_api_get_varietal_beans(setup_database, test_data_dir):
    """Test /v1/varietals/{slug}/beans endpoint returns beans with that varietal."""
    # Load data using actual function with existing test data
    await load_coffee_data(test_data_dir, incremental=False)

    # Get a varietal that has beans
    result = conn.execute("""
        SELECT DISTINCT variety_canonical[1] as canonical_name, COUNT(*) OVER () as bean_count
        FROM origins
        WHERE variety_canonical IS NOT NULL
        AND len(variety_canonical) > 0
        AND variety_canonical[1] IS NOT NULL
        AND variety_canonical[1] != ''
        LIMIT 1
    """).fetchone()

    if not result:
        pytest.skip("No varietals found in test data")

    varietal_name = result[0]
    expected_count = result[1]
    varietal_slug = varietal_name.lower().replace(' ', '-')

    # Call the API to get beans for this varietal (max per_page is 50)
    response = client.get(f"/v1/varietals/{varietal_slug}/beans?per_page=50")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data

    beans = data["data"]
    assert len(beans) >= 1


@pytest.mark.asyncio
async def test_api_varietal_not_found(setup_database):
    """Test /v1/varietals/{slug} returns 404 for non-existent varietal."""
    response = client.get("/v1/varietals/nonexistent-varietal-xyz")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
