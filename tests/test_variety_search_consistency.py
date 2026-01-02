"""
Unit tests for variety search consistency between /search and /varietals endpoints.

Tests that searching for a varietal returns the same number of beans whether
using /v1/search?variety=X or /v1/varietals/X endpoints.
"""

import os
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

# Set environment variable to use rw_kissaten.duckdb for tests
os.environ["KISSATEN_USE_RW_DB"] = "1"

# Set environment variable to ensure we're in test mode
os.environ["PYTEST_CURRENT_TEST"] = "test_variety_search_consistency.py"

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

    # Clear existing data
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


@pytest.mark.asyncio
async def test_variety_search_returns_same_count_as_varietal_endpoint(setup_database, test_data_dir):
    """Test that /v1/search?variety=X returns same bean count as /v1/varietals/X."""
    # Load data using actual function with existing test data
    await load_coffee_data(test_data_dir, incremental=False)

    # Get a varietal that has beans from the database
    result = conn.execute("""
        SELECT DISTINCT variety_canonical[1] as canonical_name, COUNT(DISTINCT cb.id) as bean_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE variety_canonical IS NOT NULL
        AND len(variety_canonical) > 0
        AND variety_canonical[1] IS NOT NULL
        AND variety_canonical[1] != ''
        GROUP BY variety_canonical[1]
        HAVING COUNT(DISTINCT cb.id) >= 2
        ORDER BY bean_count DESC
        LIMIT 1
    """).fetchone()

    if not result:
        pytest.skip("No varietals with multiple beans found in test data")

    canonical_name = result[0]
    expected_bean_count = result[1]
    varietal_slug = canonical_name.lower().replace(' ', '-')

    # Get count from /v1/varietals/{slug} endpoint
    varietals_response = client.get(f"/v1/varietals/{varietal_slug}")
    assert varietals_response.status_code == 200, f"Varietals endpoint failed for slug: {varietal_slug}"
    varietals_data = varietals_response.json()
    varietals_bean_count = varietals_data["data"]["statistics"]["total_beans"]

    # Verify it matches our database query
    assert varietals_bean_count == expected_bean_count, \
        f"Varietals endpoint returned {varietals_bean_count} beans but database has {expected_bean_count}"

    # Get count from /v1/search?variety="{canonical_name}" endpoint (exact match)
    # Using quoted search for exact match
    search_response = client.get(f'/v1/search?variety="{canonical_name}"&per_page=50')
    assert search_response.status_code == 200, "Search endpoint failed"
    search_data = search_response.json()
    search_bean_count = search_data["pagination"]["total_items"]

    # The search endpoint should return the same number of beans as the varietals endpoint
    assert search_bean_count == varietals_bean_count, \
        f"Search endpoint returned {search_bean_count} beans but varietals endpoint returned {varietals_bean_count} beans for '{canonical_name}'"


@pytest.mark.asyncio
async def test_variety_wildcard_search_includes_canonical_matches(setup_database, test_data_dir):
    """Test that /v1/search?variety=X* includes all beans with canonical variety starting with X."""
    # Load data using actual function with existing test data
    await load_coffee_data(test_data_dir, incremental=False)

    # Get a varietal prefix that has beans
    result = conn.execute("""
        SELECT DISTINCT variety_canonical[1] as canonical_name
        FROM origins o
        WHERE variety_canonical IS NOT NULL
        AND len(variety_canonical) > 0
        AND variety_canonical[1] IS NOT NULL
        AND variety_canonical[1] != ''
        AND len(variety_canonical[1]) >= 3
        LIMIT 1
    """).fetchone()

    if not result:
        pytest.skip("No varietals found in test data")

    canonical_name = result[0]
    # Use first 3 characters as prefix
    prefix = canonical_name[:3]

    # Count beans with canonical varieties starting with this prefix
    count_result = conn.execute("""
        SELECT COUNT(DISTINCT cb.id)
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id,
        unnest(o.variety_canonical) AS t(canon_var)
        WHERE t.canon_var ILIKE ?
    """, [f"{prefix}%"]).fetchone()

    expected_count = count_result[0] if count_result else 0

    if expected_count == 0:
        pytest.skip("No varietals matching prefix found")

    # Search using wildcard
    search_response = client.get(f'/v1/search?variety={prefix}*&per_page=50')
    assert search_response.status_code == 200, "Search endpoint failed"
    search_data = search_response.json()
    search_bean_count = search_data["pagination"]["total_items"]

    # The search endpoint should find all beans with canonical varieties matching the prefix
    assert search_bean_count == expected_count, \
        f"Search endpoint returned {search_bean_count} beans but expected {expected_count} beans for '{prefix}*'"


@pytest.mark.asyncio
async def test_variety_search_with_mapped_original_names(setup_database, test_data_dir):
    """Test that searching for original variety names finds beans through canonical mapping."""
    # Load data using actual function with existing test data
    await load_coffee_data(test_data_dir, incremental=False)

    # Find a canonical variety that has multiple original names mapping to it
    result = conn.execute("""
        SELECT
            variety_canonical[1] as canonical_name,
            array_agg(DISTINCT o.variety) as original_names,
            COUNT(DISTINCT cb.id) as bean_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE variety_canonical IS NOT NULL
        AND len(variety_canonical) > 0
        AND variety_canonical[1] IS NOT NULL
        AND variety_canonical[1] != ''
        AND o.variety IS NOT NULL
        AND o.variety != ''
        GROUP BY variety_canonical[1]
        HAVING COUNT(DISTINCT o.variety) > 1
        ORDER BY bean_count DESC
        LIMIT 1
    """).fetchone()

    if not result:
        pytest.skip("No varietals with multiple original names found in test data")

    canonical_name = result[0]
    original_names = result[1]
    expected_bean_count = result[2]

    # Search for the canonical name - should find all beans
    canonical_response = client.get(f'/v1/search?variety="{canonical_name}"&per_page=50')
    assert canonical_response.status_code == 200
    canonical_data = canonical_response.json()
    canonical_count = canonical_data["pagination"]["total_items"]

    assert canonical_count == expected_bean_count, \
        f"Searching for canonical name '{canonical_name}' should return {expected_bean_count} beans, got {canonical_count}"

    # Search for one of the original names - should also find all beans (through canonical mapping)
    if len(original_names) > 0 and original_names[0] != canonical_name:
        original_name = original_names[0]
        original_response = client.get(f'/v1/search?variety="{original_name}"&per_page=50')
        assert original_response.status_code == 200
        original_data = original_response.json()
        original_count = original_data["pagination"]["total_items"]

        # When searching for original name, we should find beans with that exact original name
        # This might be less than the canonical count if not all beans use that original name
        # But it should be > 0 since we know this original name exists
        assert original_count > 0, \
            f"Searching for original name '{original_name}' should find beans"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
