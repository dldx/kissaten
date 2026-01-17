"""Test that duplicate origins are not inserted into the database."""

import json
import os
import shutil
import tempfile
from pathlib import Path

# Set environment variable before importing db
temp_dir = tempfile.mkdtemp()
temp_db_path = os.path.join(temp_dir, "test.duckdb")
os.environ["KISSATEN_DATABASE_PATH"] = temp_db_path

import pytest
import pytest_asyncio

from kissaten.api.db import conn, init_database, load_coffee_data


@pytest_asyncio.fixture
async def setup_database():
    """Fixture to initialize database and clean up data before each test."""
    await init_database()
    # Clear existing data
    conn.execute("DELETE FROM origins")
    conn.execute("DELETE FROM coffee_beans")
    conn.execute("DELETE FROM roasters")
    conn.execute("DELETE FROM processed_files")
    conn.commit()
    yield
    # Cleanup after test
    conn.execute("DELETE FROM origins")
    conn.execute("DELETE FROM coffee_beans")
    conn.execute("DELETE FROM roasters")
    conn.execute("DELETE FROM processed_files")
    conn.commit()


@pytest.fixture(scope="module", autouse=True)
def cleanup_temp_db():
    """Cleanup the temporary database at the end of the module."""
    yield
    if conn:
        conn.close()
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def test_data_with_duplicates(tmp_path):
    """Create test data by copying from test_data/ and injecting duplicates."""
    # Source test data
    source_roaster_dir = Path(__file__).parent.parent / "test_data" 
    if not source_roaster_dir.exists():
        pytest.skip(f"Source test data not found at {source_roaster_dir}")

    return source_roaster_dir


@pytest.mark.asyncio
async def test_duplicate_origins_deduplication(setup_database, test_data_with_duplicates):
    """Test that duplicate origins are effectively deduplicated when loading."""
    await load_coffee_data(test_data_with_duplicates, incremental=False, check_for_changes=False)

    # Get the bean ID
    bean_id = conn.execute("SELECT id from coffee_beans where clean_url_slug = 'tabe_burka_washed_010019';").fetchone()[0]
    assert bean_id is not None

    # Check origin count - should be 1, not 2
    count = conn.execute("SELECT COUNT(*) FROM origins WHERE bean_id = ?", [bean_id]).fetchone()[0]
    
    assert count == 1, f"Expected 1 origin, but found {count} for bean_id {bean_id}"
