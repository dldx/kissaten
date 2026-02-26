"""
Shared pytest fixtures for the Kissaten API test suite.

IMPORTANT: The KISSATEN_USE_RW_DB env var must be set BEFORE any kissaten module is
imported, because ``kissaten.api.db.conn`` is created at module-load time and the DB
path depends on the env var at that moment.
"""
import os

# Must be set before any kissaten import so db.py picks the rw database.
os.environ["KISSATEN_USE_RW_DB"] = "1"

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from kissaten.api.db import conn, init_database, load_coffee_data
from kissaten.api.main import app

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TEST_DATA_DIR = Path(__file__).parent.parent / "test_data" / "roasters"

_TABLES = [
    "origins",
    "coffee_beans",
    "roasters",
    "country_codes",
    "roaster_location_codes",
    "tasting_notes_categories",
    "processed_files",
]

# ---------------------------------------------------------------------------
# Session-scoped fixtures  (run once per test session)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def db_session():
    """Initialise DB schema and load test data once for the whole session."""
    if not _TEST_DATA_DIR.exists():
        pytest.skip(f"Test data directory not found: {_TEST_DATA_DIR}")
    await init_database()
    await load_coffee_data(_TEST_DATA_DIR)
    yield


@pytest.fixture(scope="session")
def client(db_session):
    """Session-scoped TestClient.  Depends on db_session to ensure data is loaded.

    Use the context-manager form so that:
    - Lifespan startup runs immediately (registers FX/AI search routers).
    - conn.close() in lifespan shutdown only fires at session teardown,
      after all tests have finished.
    """
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Function-scoped fixtures  (run before/after every data-modifying test)
# ---------------------------------------------------------------------------


@pytest.fixture
def test_data_dir():
    """Return the shared test data directory path."""
    if not _TEST_DATA_DIR.exists():
        pytest.skip(f"Test data directory not found: {_TEST_DATA_DIR}")
    return _TEST_DATA_DIR


@pytest_asyncio.fixture
async def setup_database(db_session):
    """Function-scoped fixture for data-modifying tests.

    Truncates all tables *before* the test so each test starts with an empty DB.
    In teardown, truncates again and reloads the shared test dataset so the
    session state is restored for subsequent read-only tests.
    """
    for tbl in _TABLES:
        conn.execute(f"TRUNCATE TABLE {tbl}")
    conn.commit()

    yield

    for tbl in _TABLES:
        conn.execute(f"TRUNCATE TABLE {tbl}")
    conn.commit()
    await load_coffee_data(_TEST_DATA_DIR)
