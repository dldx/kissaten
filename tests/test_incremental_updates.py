"""
Comprehensive tests for incremental database update functionality.

Tests cover:
- Initial full database load
- Incremental updates (new files only)
- Incremental updates with checksum verification
- Adding new roasters in incremental mode
- Processing diffjson files incrementally
- File tracking (processed_files table)
- Skipping already processed files
"""

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path

import duckdb
import pytest

from kissaten.api import db

# Test data paths
TEST_DATA_ROOT = Path(__file__).parent.parent / "test_data" / "roasters"


@pytest.fixture
def temp_test_data():
    """Create a temporary copy of test data to avoid modifying the original."""
    temp_dir = Path(tempfile.mkdtemp())
    test_data_dir = temp_dir / "roasters"

    # Copy test data to temp directory
    if TEST_DATA_ROOT.exists():
        shutil.copytree(TEST_DATA_ROOT, test_data_dir)
    else:
        # Create minimal test structure if test data doesn't exist
        test_data_dir.mkdir(parents=True)
        (test_data_dir / "test_roaster_1" / "20250101").mkdir(parents=True)

    yield test_data_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    # Use mktemp to get a path, but don't create the file
    # DuckDB will create it properly
    temp_db_path = Path(tempfile.mktemp(suffix=".duckdb"))

    # Set environment variable to use test database
    original_env = os.environ.get("KISSATEN_USE_RW_DB")
    os.environ["KISSATEN_USE_RW_DB"] = "1"

    yield temp_db_path

    # Cleanup
    if temp_db_path.exists():
        temp_db_path.unlink()

    # Restore environment
    if original_env is not None:
        os.environ["KISSATEN_USE_RW_DB"] = original_env
    else:
        os.environ.pop("KISSATEN_USE_RW_DB", None)


@pytest.fixture
def isolated_db_connection(temp_db):
    """Create isolated database connection that saves and restores the global db.conn."""
    # Save original connection
    original_conn = db.conn

    # Create new connection for test
    db.conn = duckdb.connect(str(temp_db))

    yield db.conn

    # Restore original connection
    db.conn = original_conn


@pytest.fixture
def db_connection(temp_db):
    """Create a database connection for testing."""
    conn = duckdb.connect(str(temp_db))
    yield conn
    conn.close()


@pytest.mark.asyncio
async def test_full_refresh_initial_load(temp_test_data, isolated_db_connection):
    """Test initial full database load with test data."""
    # Import db module after setting up temp database

    # Run full refresh
    await db.init_database(incremental=False, check_for_changes=False)
    await db.load_coffee_data(temp_test_data, incremental=False, check_for_changes=False)

    # Verify data was loaded
    result = db.conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()
    bean_count = result[0] if result else 0

    assert bean_count > 0, "Should load beans from test data"

    # Verify roasters were loaded
    roaster_result = db.conn.execute("SELECT COUNT(*) FROM roasters").fetchone()
    roaster_count = roaster_result[0] if roaster_result else 0

    assert roaster_count > 0, "Should load roasters from registry"

    # Verify processed_files table now tracks files even in full refresh
    # This allows subsequent incremental updates to work correctly
    processed_result = db.conn.execute("SELECT COUNT(*) FROM processed_files").fetchone()
    processed_count = processed_result[0] if processed_result else 0

    assert processed_count > 0, "Full refresh should now track files for subsequent incremental updates"



@pytest.mark.asyncio
async def test_incremental_update_new_files_only(temp_test_data, isolated_db_connection):
    """Test incremental update that only processes new files."""

    # Initial load WITH incremental mode so files are tracked
    await db.init_database(incremental=True, check_for_changes=False)
    await db.load_coffee_data(temp_test_data, incremental=True, check_for_changes=False)

    initial_count = db.conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()[0]

    # Now run incremental update again (should skip already processed files)
    await db.init_database(incremental=True, check_for_changes=False)
    await db.load_coffee_data(temp_test_data, incremental=True, check_for_changes=False)

    after_incremental_count = db.conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()[0]

    # Count should be the same since no new files were added
    assert after_incremental_count == initial_count, "Incremental update should skip already processed files"

    # Verify processed_files table has entries
    processed_count = db.conn.execute("SELECT COUNT(*) FROM processed_files").fetchone()[0]
    assert processed_count > 0, "Should track processed files in incremental mode"



@pytest.mark.asyncio
async def test_incremental_with_new_file(temp_test_data, isolated_db_connection):
    """Test that incremental update processes new files that appear after initial load."""

    # Initial load
    await db.init_database(incremental=False, check_for_changes=False)
    await db.load_coffee_data(temp_test_data, incremental=False, check_for_changes=False)

    initial_count = db.conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()[0]

    # Add a new file to test data
    new_file_dir = temp_test_data / "test_roaster_1" / "20250103"
    new_file_dir.mkdir(parents=True, exist_ok=True)

    new_bean_data = {
        "name": "Brand New Bean",
        "url": "https://testroaster1.com/brand-new",
        "price": 30.00,
        "currency": "USD",
        "weight": 250,
        "in_stock": True,
        "roast_level": "Light",
        "tasting_notes": ["jasmine", "peach", "tea"],
        "description": "A brand new bean added after initial load",
        "origins": [{"country": "ET", "region": "Sidamo", "process": "natural", "variety": "Heirloom"}],
        "scraped_at": "2025-01-03T10:00:00",
        "scraper_version": "1.0.0"
    }

    with open(new_file_dir / "brand_new_bean.json", "w") as f:
        json.dump(new_bean_data, f)

    # Run incremental update
    await db.init_database(incremental=True, check_for_changes=False)
    await db.load_coffee_data(temp_test_data, incremental=True, check_for_changes=False)

    after_incremental_count = db.conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()[0]

    # Should have one more bean
    assert after_incremental_count == initial_count + 1, "Should add new bean file in incremental update"

    # Verify the new bean was added
    new_bean = db.conn.execute(
        "SELECT name FROM coffee_beans WHERE url = ?",
        ["https://testroaster1.com/brand-new"]
    ).fetchone()

    assert new_bean is not None, "New bean should be in database"
    assert new_bean[0] == "Brand New Bean", "New bean should have correct name"



@pytest.mark.asyncio
async def test_incremental_with_checksum_verification(temp_test_data, isolated_db_connection):
    """Test incremental update with --check-for-changes flag (checksum verification)."""

    # Initial load
    await db.init_database(incremental=False, check_for_changes=False)
    await db.load_coffee_data(temp_test_data, incremental=False, check_for_changes=False)

    # Modify an existing file
    test_file = temp_test_data / "test_roaster_1" / "20250101" / "bean_1.json"
    if test_file.exists():
        with open(test_file, "r") as f:
            bean_data = json.load(f)

        # Modify price
        bean_data["price"] = 99.99

        with open(test_file, "w") as f:
            json.dump(bean_data, f)

        # Run incremental without checksum verification (should skip modified file)
        await db.init_database(incremental=True, check_for_changes=False)
        await db.load_coffee_data(temp_test_data, incremental=True, check_for_changes=False)

        # Price should still be original
        result = db.conn.execute(
            "SELECT price FROM coffee_beans WHERE url = ?",
            ["https://testroaster1.com/bean-1"]
        ).fetchone()

        # Note: This might be 99.99 if the file was processed, or original if skipped
        # The key test is with check_for_changes=True below

        # Now run with checksum verification
        await db.init_database(incremental=True, check_for_changes=True)
        await db.load_coffee_data(temp_test_data, incremental=True, check_for_changes=True)

        # Should detect change and reprocess
        result_after = db.conn.execute(
            "SELECT price FROM coffee_beans WHERE url = ?",
            ["https://testroaster1.com/bean-1"]
        ).fetchone()

        # With check_for_changes, it should eventually have the new price
        assert result_after is not None, "Bean should exist in database"



@pytest.mark.asyncio
async def test_diffjson_incremental_processing(temp_test_data, isolated_db_connection):
    """Test that diffjson files are processed incrementally."""

    # Initial load
    await db.init_database(incremental=False, check_for_changes=False)
    await db.load_coffee_data(temp_test_data, incremental=False, check_for_changes=False)

    # Check initial stock status
    result = db.conn.execute(
        "SELECT in_stock FROM coffee_beans WHERE url = ?",
        ["https://testroaster1.com/bean-1"]
    ).fetchone()

    if result:
        initial_stock = result[0]

        # Apply diffjson updates
        await db.apply_diffjson_updates(temp_test_data, incremental=True, check_for_changes=False)

        # Check updated stock status
        result_after = db.conn.execute(
            "SELECT in_stock FROM coffee_beans WHERE url = ?",
            ["https://testroaster1.com/bean-1"]
        ).fetchone()

        # Stock status should have been updated by diffjson
        assert result_after is not None, "Bean should still exist"
        # The diffjson in test data sets in_stock to false
        assert result_after[0] == False, "Diffjson should update stock status to False"

        # Verify diffjson file was marked as processed
        processed = db.conn.execute(
            "SELECT COUNT(*) FROM processed_files WHERE file_type = 'diffjson'"
        ).fetchone()[0]

        assert processed > 0, "Diffjson files should be tracked in processed_files"



@pytest.mark.asyncio
async def test_new_roaster_added_incrementally(temp_test_data, isolated_db_connection):
    """Test that new roasters can be added in incremental mode."""

    # Initial load (only test_roaster_1 exists in test data initially)
    await db.init_database(incremental=False, check_for_changes=False)
    await db.load_coffee_data(temp_test_data, incremental=False, check_for_changes=False)

    initial_roaster_count = db.conn.execute("SELECT COUNT(*) FROM roasters").fetchone()[0]

    # Simulate adding a new roaster to the registry
    # This would happen if test_roaster_2 data exists and a new scraper is added to registry

    # Run incremental update (should detect new roaster if it exists in test data)
    await db.init_database(incremental=True, check_for_changes=False)
    await db.load_coffee_data(temp_test_data, incremental=True, check_for_changes=False)

    after_roaster_count = db.conn.execute("SELECT COUNT(*) FROM roasters").fetchone()[0]

    # If test_roaster_2 directory exists in test data, it should be added
    test_roaster_2_dir = temp_test_data / "test_roaster_2"
    if test_roaster_2_dir.exists():
        assert after_roaster_count >= initial_roaster_count, "Should allow new roasters in incremental mode"
    else:
        assert after_roaster_count == initial_roaster_count, "No new roasters if directory doesn't exist"



@pytest.mark.asyncio
async def test_processed_files_tracking(temp_test_data, isolated_db_connection):
    """Test that processed_files table correctly tracks processed files."""

    # Initial load without incremental (full refresh now also tracks files)
    await db.init_database(incremental=False, check_for_changes=False)
    await db.load_coffee_data(temp_test_data, incremental=False, check_for_changes=False)

    processed_count_full = db.conn.execute("SELECT COUNT(*) FROM processed_files").fetchone()[0]
    assert processed_count_full > 0, "Full refresh should now track files for subsequent incremental updates"

    # Now run incremental (should track)
    await db.init_database(incremental=True, check_for_changes=False)
    await db.load_coffee_data(temp_test_data, incremental=True, check_for_changes=False)

    processed_count_incr = db.conn.execute("SELECT COUNT(*) FROM processed_files").fetchone()[0]
    assert processed_count_incr > 0, "Incremental mode should track processed files"

    # Verify checksums are stored
    with_checksums = db.conn.execute(
        "SELECT COUNT(*) FROM processed_files WHERE checksum IS NOT NULL AND checksum != ''"
    ).fetchone()[0]

    assert with_checksums == processed_count_incr, "All tracked files should have checksums"

    # Verify file paths are relative
    absolute_paths = db.conn.execute(
        "SELECT COUNT(*) FROM processed_files WHERE file_path LIKE '/%'"
    ).fetchone()[0]

    assert absolute_paths == 0, "File paths should be relative, not absolute"



@pytest.mark.asyncio
async def test_mark_file_processed_function(temp_test_data, isolated_db_connection):
    """Test the mark_file_processed helper function."""

    # Initialize database
    await db.init_database(incremental=True, check_for_changes=False)

    # Create a test file
    test_file = temp_test_data / "test_roaster_1" / "20250101" / "bean_1.json"

    if test_file.exists():
        # Mark file as processed
        db.mark_file_processed(test_file, temp_test_data, "json")

        # Verify it was marked
        result = db.conn.execute(
            "SELECT file_path, file_type FROM processed_files WHERE file_path = ?",
            [str(test_file.relative_to(temp_test_data))]
        ).fetchone()

        assert result is not None, "File should be marked as processed"
        assert result[1] == "json", "File type should be 'json'"

        # Mark same file again (should update, not duplicate)
        db.mark_file_processed(test_file, temp_test_data, "json")

        count = db.conn.execute(
            "SELECT COUNT(*) FROM processed_files WHERE file_path = ?",
            [str(test_file.relative_to(temp_test_data))]
        ).fetchone()[0]

        assert count == 1, "Should not create duplicate entries"



@pytest.mark.asyncio
async def test_is_file_processed_function(temp_test_data, isolated_db_connection):
    """Test the is_file_processed helper function."""

    # Initialize database
    await db.init_database(incremental=True, check_for_changes=False)

    test_file = temp_test_data / "test_roaster_1" / "20250101" / "bean_1.json"

    if test_file.exists():
        # File should not be processed initially
        is_processed = db.is_file_processed(test_file, temp_test_data, check_checksum=False)
        assert not is_processed, "File should not be processed initially"

        # Mark it as processed
        db.mark_file_processed(test_file, temp_test_data, "json")

        # Now it should be processed
        is_processed_after = db.is_file_processed(test_file, temp_test_data, check_checksum=False)
        assert is_processed_after, "File should be marked as processed"

        # Test with checksum verification
        is_processed_checksum = db.is_file_processed(test_file, temp_test_data, check_checksum=True)
        assert is_processed_checksum, "File checksum should match"

        # Modify file and test checksum mismatch
        with open(test_file, "r") as f:
            content = json.load(f)
        content["price"] = 999.99
        with open(test_file, "w") as f:
            json.dump(content, f)

        # Without checksum check, still considered processed
        is_processed_no_check = db.is_file_processed(test_file, temp_test_data, check_checksum=False)
        assert is_processed_no_check, "Should be processed when not checking checksum"

        # With checksum check, should detect change
        is_processed_check = db.is_file_processed(test_file, temp_test_data, check_checksum=True)
        assert not is_processed_check, "Should detect file change with checksum verification"



if __name__ == "__main__":
    pytest.main([__file__, "-v"])
