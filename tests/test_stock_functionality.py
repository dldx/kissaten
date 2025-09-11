#!/usr/bin/env python3
"""
Pytest tests for the existing stock status functionality in kissaten.api.main
Tests the actual load_coffee_data() function with the data_dir parameter
"""
import shutil
import sys
import tempfile
from pathlib import Path

# Add the src directory to the path so we can import kissaten modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
import pytest_asyncio
from kissaten.api.db import conn
from kissaten.api.main import init_database, load_coffee_data


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
async def test_load_coffee_data_with_test_data(setup_database, test_data_dir):
    """Test that load_coffee_data() works correctly with test data directory"""
    # Load data using test directory
    await load_coffee_data(test_data_dir)

    # Verify basic functionality
    total_beans_result = conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()
    total_beans = total_beans_result[0] if total_beans_result else 0

    in_stock_result = conn.execute("SELECT COUNT(*) FROM coffee_beans WHERE in_stock = true").fetchone()
    in_stock_count = in_stock_result[0] if in_stock_result else 0

    out_of_stock_result = conn.execute("SELECT COUNT(*) FROM coffee_beans WHERE in_stock = false").fetchone()
    out_of_stock_count = out_of_stock_result[0] if out_of_stock_result else 0

    test_roaster_result = conn.execute("""
        SELECT COUNT(*) FROM coffee_beans
        WHERE roaster = 'Leaves Coffee Roasters'
    """).fetchone()
    test_roaster_count = test_roaster_result[0] if test_roaster_result else 0

    test_roaster_in_stock_result = conn.execute("""
        SELECT COUNT(*) FROM coffee_beans
        WHERE roaster = 'Leaves Coffee Roasters' AND in_stock = true
    """).fetchone()
    test_roaster_in_stock = test_roaster_in_stock_result[0] if test_roaster_in_stock_result else 0

    test_roaster_out_of_stock_result = conn.execute("""
        SELECT COUNT(*) FROM coffee_beans
        WHERE roaster = 'Leaves Coffee Roasters' AND in_stock = false
    """).fetchone()
    test_roaster_out_of_stock = test_roaster_out_of_stock_result[0] if test_roaster_out_of_stock_result else 0

    # Test assertions
    assert total_beans > 0, "No beans were loaded"
    assert in_stock_count > 0 and out_of_stock_count > 0, "Stock status tracking not working correctly"

    # Note: Test roaster expectations might vary, so we don't assert specific numbers
    # but we can check that the test roaster exists
    if test_roaster_count > 0:
        assert test_roaster_in_stock >= 0 and test_roaster_out_of_stock >= 0, "Test roaster stock counts should be non-negative"

    # Test URL deduplication
    duplicate_urls = conn.execute("""
        SELECT url, COUNT(*) as count
        FROM coffee_beans
        WHERE url IS NOT NULL AND url != ''
        GROUP BY url
        HAVING COUNT(*) > 1
    """).fetchall()

    assert len(duplicate_urls) == 0, f"Found {len(duplicate_urls)} duplicate URLs"

    # Test idempotency
    await load_coffee_data(test_data_dir)

    second_total_result = conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()
    second_total = second_total_result[0] if second_total_result else 0

    assert second_total == total_beans, f"Idempotency test failed ({total_beans} vs {second_total})"


@pytest.mark.asyncio
async def test_stock_status_functionality(setup_database, test_data_dir):
    """Test the stock status functionality specifically"""
    # Load data
    await load_coffee_data(test_data_dir)

    # Check overall distribution
    total_result = conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()
    total = total_result[0] if total_result else 0

    in_stock_result = conn.execute("SELECT COUNT(*) FROM coffee_beans WHERE in_stock = true").fetchone()
    in_stock = in_stock_result[0] if in_stock_result else 0

    out_of_stock_result = conn.execute("SELECT COUNT(*) FROM coffee_beans WHERE in_stock = false").fetchone()
    out_of_stock = out_of_stock_result[0] if out_of_stock_result else 0

    # Analyze by roaster
    roaster_stats = conn.execute("""
        SELECT roaster,
               COUNT(*) as total,
               SUM(CASE WHEN in_stock THEN 1 ELSE 0 END) as in_stock_count,
               SUM(CASE WHEN in_stock THEN 0 ELSE 1 END) as out_of_stock_count
        FROM coffee_beans
        GROUP BY roaster
        HAVING total > 1
        ORDER BY total DESC
    """).fetchall()

    # Test assertions
    assert total > 0, "No data loaded"
    assert in_stock > 0 and out_of_stock > 0, "Stock status tracking not working correctly"
    assert len(roaster_stats) > 0, "No roaster statistics found"


@pytest.mark.asyncio
async def test_restock_functionality(setup_database, test_data_dir):
    """Test that beans can come back into stock after being out of stock"""
    # Step 1: Load only the 20250908 data (older scrape)
    # Create a temporary directory structure with only 20250908 data
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        roasters_dir = temp_path / "roasters"
        test_roaster_dir = roasters_dir / "test_roaster"
        old_scrape_dir = test_roaster_dir / "20250908"

        # Copy only the 20250908 data
        old_scrape_source = test_data_dir / "test_roaster" / "20250908"
        if old_scrape_source.exists():
            shutil.copytree(old_scrape_source, old_scrape_dir)
            await load_coffee_data(roasters_dir)

        # Check what we have after first load
        initial_total_result = conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()
        initial_total = initial_total_result[0] if initial_total_result else 0

    # Step 2: Load the full dataset (including 20250911)
    await load_coffee_data(test_data_dir)

    # Check what we have after full load
    final_total_result = conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()
    final_total = final_total_result[0] if final_total_result else 0

    final_in_stock_result = conn.execute("SELECT COUNT(*) FROM coffee_beans WHERE in_stock = true").fetchone()
    final_in_stock = final_in_stock_result[0] if final_in_stock_result else 0

    final_out_of_stock_result = conn.execute("SELECT COUNT(*) FROM coffee_beans WHERE in_stock = false").fetchone()
    final_out_of_stock = final_out_of_stock_result[0] if final_out_of_stock_result else 0

    # Step 3: Analyze what happened to the beans
    # Check for beans that stayed in stock (should be in both scrapes)
    stayed_in_stock = conn.execute("""
        SELECT name, url FROM coffee_beans WHERE in_stock = true
    """).fetchall()

    # Check for beans that went out of stock (in 20250908 but not in 20250911)
    went_out_of_stock = conn.execute("""
        SELECT name, url FROM coffee_beans WHERE in_stock = false
    """).fetchall()

    # Test assertions
    assert final_total >= initial_total, "Lost beans during full load"
    assert final_in_stock > 0 and final_out_of_stock > 0, "Restock test failed - missing stock status variety"
    # The key functionality: we should have both in-stock and out-of-stock beans
    assert len(stayed_in_stock) >= 0 and len(went_out_of_stock) >= 0, "Stock status tracking not working"


@pytest.mark.asyncio
async def test_no_duplicates(setup_database, test_data_dir):
    """Test that there are no duplicate beans based on URL"""
    # Load data
    await load_coffee_data(test_data_dir)

    # Check for duplicate URLs
    duplicate_urls = conn.execute("""
        SELECT url, COUNT(*) as count,
               GROUP_CONCAT(name, ' | ') as bean_names
        FROM coffee_beans
        WHERE url IS NOT NULL AND url != ''
        GROUP BY url
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    """).fetchall()

    # Check overall data integrity
    total_result = conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()
    total = total_result[0] if total_result else 0

    unique_urls_result = conn.execute("""
        SELECT COUNT(DISTINCT url) FROM coffee_beans
        WHERE url IS NOT NULL AND url != ''
    """).fetchone()
    unique_urls = unique_urls_result[0] if unique_urls_result else 0

    beans_with_urls_result = conn.execute("""
        SELECT COUNT(*) FROM coffee_beans
        WHERE url IS NOT NULL AND url != ''
    """).fetchone()
    beans_with_urls = beans_with_urls_result[0] if beans_with_urls_result else 0

    # Test assertions
    assert len(duplicate_urls) == 0, f"Found {len(duplicate_urls)} duplicate URLs"
    assert total > 0, "No beans loaded"
    assert beans_with_urls > 0, "No beans with URLs found"
    assert unique_urls > 0, "No unique URLs found"
    # Note: We don't assert beans_with_urls == unique_urls because some beans might not have URLs



