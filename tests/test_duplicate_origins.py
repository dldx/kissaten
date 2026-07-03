"""Test that duplicate origins are not inserted into the database."""

from pathlib import Path

import pytest

from kissaten.api.db import conn, load_coffee_data


@pytest.fixture
def test_data_with_duplicates():
    """Return the test data root (parent of ``roasters/``) so ``load_coffee_data``
    globs every JSON file in the tree, including the ``substance_café`` fixture
    that intentionally contains a duplicate origin to exercise dedup."""
    source_roaster_dir = Path(__file__).parent.parent / "test_data"
    if not source_roaster_dir.exists():
        pytest.skip(f"Source test data not found at {source_roaster_dir}")
    return source_roaster_dir


@pytest.mark.asyncio
async def test_duplicate_origins_deduplication(setup_database, test_data_with_duplicates):
    """Test that duplicate origins are effectively deduplicated when loading."""
    await load_coffee_data(test_data_with_duplicates, incremental=False, check_for_changes=False)

    bean_id = conn.execute(
        "SELECT id FROM coffee_beans WHERE clean_url_slug = 'tabe_burka_washed_010019';"
    ).fetchone()[0]
    assert bean_id is not None

    count = conn.execute("SELECT COUNT(*) FROM origins WHERE bean_id = ?", [bean_id]).fetchone()[0]

    assert count == 1, f"Expected 1 origin, but found {count} for bean_id {bean_id}"
