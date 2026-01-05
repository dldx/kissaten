"""
Test consistency of bean statistics across different endpoints for the same region.

This test suite compares bean counts from:
1. Region detail endpoint (/api/v1/origins/{country}/{region})
2. Region farms endpoint (/api/v1/origins/{country}/{region}/farms)
3. Search endpoint (/api/v1/search?origin={country}&region={region})

These should all return consistent results for the same region.
"""

import pytest
import pytest_asyncio
from pathlib import Path
from kissaten.api.db import conn, init_database, load_coffee_data

@pytest_asyncio.fixture
async def setup_database():
    """Fixture to initialize database and clean up data before each test"""
    await init_database()
    # Clear existing data
    conn.execute("DELETE FROM origins")
    conn.execute("DELETE FROM coffee_beans")
    conn.execute("DELETE FROM roasters")
    conn.commit()
    yield
    # Cleanup after test
    conn.execute("DELETE FROM origins")
    conn.execute("DELETE FROM coffee_beans")
    conn.execute("DELETE FROM roasters")
    conn.commit()


@pytest.fixture
def test_data_dir():
    """Fixture to provide test data directory path"""
    test_dir = Path(__file__).parent.parent / "test_data" / "roasters"
    if not test_dir.exists():
        pytest.skip(f"Test data directory not found: {test_dir}")
    return test_dir


@pytest.mark.asyncio
async def test_region_statistics_consistency(setup_database, test_data_dir):
    """Test that bean statistics are consistent across all endpoints for a region"""
    from kissaten.api.main import get_region_detail, search_coffee_beans

    # Load test data
    await load_coffee_data(test_data_dir)

    # First, find a region that exists in the test data
    region_query = """
        SELECT DISTINCT
            o.country,
            o.region,
            o.region_normalized as region_slug,
            get_canonical_state(o.country, o.region) as canonical_state,
            COUNT(DISTINCT cb.id) as bean_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.region IS NOT NULL AND o.region != ''
        GROUP BY o.country, o.region, o.region_normalized, canonical_state
        ORDER BY bean_count DESC
        LIMIT 1
    """
    region_data_row = conn.execute(region_query).fetchone()

    if not region_data_row:
        pytest.skip("No regions found in test data")

    country_code = region_data_row[0]
    region_name = region_data_row[1]
    region_slug = region_data_row[2]
    canonical_state = region_data_row[3]
    expected_bean_count = region_data_row[4]

    print(f"\n=== Testing Region: {region_name} ({country_code}) ===")
    print(f"Region slug: {region_slug}")
    print(f"Canonical state: {canonical_state}")
    print(f"Expected bean count from DB: {expected_bean_count}")

    # 1. Get statistics from region detail endpoint
    region_detail_response = await get_region_detail(country_code, region_slug)
    assert region_detail_response.success, "Region detail endpoint failed"
    region_data = region_detail_response.data

    total_beans_from_detail = region_data.statistics.total_beans
    print(f"\n1. Region Detail Endpoint: {total_beans_from_detail} beans")

    # 2. Get farm statistics from the SAME response (endpoint consolidated)
    farms_data = region_data.top_farms

    # Sum up bean counts from all farms
    total_beans_from_farms = sum(farm.bean_count for farm in farms_data)
    print(f"2. Farm Data (from Detail Endpoint): {total_beans_from_farms} beans (summed from farms)")

    # 3. Simulate search endpoint filtering logic
    # The search endpoint uses "o.region ILIKE ?" for region filtering
    search_simulation_query = """
        SELECT COUNT(DISTINCT cb.id) as total_beans
        FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY clean_url_slug ORDER BY scraped_at DESC) as rn
            FROM coffee_beans_with_origin cb
        ) cb
        WHERE cb.rn = 1
        AND EXISTS (SELECT 1 FROM origins o WHERE o.bean_id = cb.id AND o.country = ? AND o.region ILIKE ?)
    """
    search_sim_result = conn.execute(search_simulation_query, [country_code, f"%{region_name}%"]).fetchone()
    total_beans_from_search = search_sim_result[0] if search_sim_result else 0
    print(f"3. Search Simulation (ILIKE matching): {total_beans_from_search} beans")

    # 4. Check varietal counts from region detail
    total_beans_from_varietals = sum(v.count for v in region_data.varietals)
    print(f"4. Sum of Varietal Counts: {total_beans_from_varietals} beans")

    # 5. Direct database query to verify ground truth
    # Use the same region filter as region_detail endpoint
    direct_query = """
        SELECT COUNT(DISTINCT cb.id) as total_beans
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.country = ?
        AND (
            normalize_region_name(get_canonical_state(o.country, o.region)) = ?
            OR o.region_normalized = ?
        )
    """
    direct_result = conn.execute(direct_query, [country_code, region_slug, region_slug]).fetchone()
    total_beans_direct = direct_result[0] if direct_result else 0
    print(f"5. Direct DB Query (with canonical state): {total_beans_direct} beans")

    #  6. Query without canonical state (simulating current search endpoint behavior)
    # Search endpoint only uses o.region ILIKE, doesn't consider canonical states
    search_only_query = """
        SELECT COUNT(DISTINCT cb.id) as total_beans
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.country = ? AND o.region ILIKE ?
    """
    search_only_result = conn.execute(search_only_query, [country_code, f"%{region_name}%"]).fetchone()
    total_beans_search_only = search_only_result[0] if search_only_result else 0
    print(f"6. Search-Style Query (no canonical state): {total_beans_search_only} beans")

    # 7. List all actual region values in the database for this country
    region_values_query = """
        SELECT DISTINCT
            o.region,
            get_canonical_state(o.country, o.region) as canonical_state,
            o.region_normalized as normalized,
            COUNT(DISTINCT cb.id) as bean_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.country = ?
        GROUP BY o.region, canonical_state, o.region_normalized
        ORDER BY bean_count DESC
    """
    region_values = conn.execute(region_values_query, [country_code]).fetchall()
    print(f"\n7. All regions in database for {country_code}:")
    for row in region_values:
        print(f"   - Region: '{row[0]}' | Canonical: '{row[1]}' | Normalized: '{row[2]}' | Beans: {row[3]}")

    # ASSERTIONS
    print("\n=== CONSISTENCY CHECKS ===")

    # The region detail and direct DB query should match (they use the same logic)
    assert total_beans_from_detail == total_beans_direct, (
        f"Region detail endpoint ({total_beans_from_detail}) doesn't match "
        f"direct DB query with canonical state ({total_beans_direct})"
    )
    print(f"✓ Region detail matches direct DB query: {total_beans_from_detail} beans")

    # Search endpoint should match the region detail (if region filtering is consistent)
    assert total_beans_from_search == total_beans_from_detail, (
        f"Search endpoint ({total_beans_from_search}) doesn't match "
        f"region detail endpoint ({total_beans_from_detail}). "
        f"This suggests search is not using canonical state mapping for region filtering."
    )
    print(f"✓ Search endpoint matches region detail: {total_beans_from_search} beans")

    # Varietal counts should match total beans (note: varietals may have duplicates across origins)
    # This assertion may not always hold if beans have multiple origins with same variety
    # So we make it informational rather than strict
    if total_beans_from_varietals != total_beans_from_detail:
        print(f"⚠ Warning: Varietal sum ({total_beans_from_varietals}) != total beans ({total_beans_from_detail})")
        print("  This may indicate beans with multiple origins or variety_canonical expansion")
    else:
        print(f"✓ Varietal sum matches total beans: {total_beans_from_varietals} beans")

    # Farm bean counts should be <= total beans (farms can be NULL)
    # Note: farm counts may not sum to total beans if some beans don't have farm data
    if total_beans_from_farms > total_beans_from_detail:
        pytest.fail(
            f"Farm beans ({total_beans_from_farms}) exceeds total beans ({total_beans_from_detail}). "
            f"This suggests farms endpoint is including beans from outside the region."
        )
    elif total_beans_from_farms < total_beans_from_detail:
        print(f"⚠ Note: Farm sum ({total_beans_from_farms}) < total beans ({total_beans_from_detail})")
        print("  This is expected if some beans don't have farm information")
    else:
        print(f"✓ Farm sum matches total beans: {total_beans_from_farms} beans")


@pytest.mark.asyncio
async def test_search_region_filter_with_canonical_state(setup_database, test_data_dir):
    """Test that search endpoint correctly uses canonical state for region filtering"""
    from kissaten.api.main import search_coffee_beans

    # Load test data
    await load_coffee_data(test_data_dir)

    # Test case: Search by different region name variations
    country_code = "CO"

    # Query all distinct regions for Colombia to understand the data
    region_query = """
        SELECT DISTINCT
            o.region,
            get_canonical_state(o.country, o.region) as canonical_state,
            COUNT(DISTINCT cb.id) as bean_count
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE o.country = ?
        GROUP BY o.region, canonical_state
        ORDER BY bean_count DESC
    """
    regions = conn.execute(region_query, [country_code]).fetchall()

    print(f"\n=== Testing Search Region Filtering ===")
    print(f"\nRegions in database for {country_code}:")
    for row in regions:
        print(f"  - Region: '{row[0]}' | Canonical: '{row[1]}' | Beans: {row[2]}")

    # Test searching by different variations of the same region
    if regions:
        # Take the first region with a canonical state mapping
        test_region = None
        canonical_state = None
        for row in regions:
            if row[1] is not None:  # Has canonical state
                test_region = row[0]
                canonical_state = row[1]
                expected_count = row[2]
                break

        if test_region and canonical_state:
            print(f"\nTest: Searching by original region '{test_region}' vs canonical '{canonical_state}'")

            # Search by original region name
            response1 = await search_coffee_beans(
                origin=[country_code],
                region=test_region,
                in_stock_only=False,
                page=1,
                per_page=100
            )
            count1 = response1.data.pagination.total if response1.success else 0
            print(f"  Original region search: {count1} beans")

            # Search by canonical state
            response2 = await search_coffee_beans(
                origin=[country_code],
                region=canonical_state,
                in_stock_only=False,
                page=1,
                per_page=100
            )
            count2 = response2.data.pagination.total if response2.success else 0
            print(f"  Canonical state search: {count2} beans")

            # They should return the same results if search uses canonical state mapping
            assert count1 == count2, (
                f"Search by original region '{test_region}' ({count1} beans) "
                f"doesn't match search by canonical state '{canonical_state}' ({count2} beans). "
                f"Search endpoint should use canonical state mapping."
            )
            print(f"  ✓ Both searches return same count: {count1} beans")
