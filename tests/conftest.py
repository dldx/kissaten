"""
Shared pytest fixtures for the Kissaten API test suite.

Database isolation
------------------
The conftest redirects the module-level ``kissaten.api.db.conn`` to a
session-scoped temporary DuckDB file via ``KISSATEN_DATABASE_PATH``. The
safety guard in ``db.py`` treats the temp path as safe (it only refuses
``data/rw_kissaten.duckdb`` and ``data/kissaten.duckdb``), so the developer's
working database is never at risk of being overwritten by a test run.

We also set ``KISSATEN_USE_RW_DB=1`` so the connection gets the permissive
DuckDB config (``{}``) that ``load_coffee_data`` requires for its
``read_json`` / filesystem glob operations. This mirrors the production
``kissaten refresh`` workflow but redirects at a temp file.

IMPORTANT: both env vars must be set BEFORE any ``kissaten`` import, because
``kissaten.api.db.conn`` is created at module-load time.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Compute a session-scoped temp DB path before importing kissaten so the
# import-time env-var check in db.py sees it.
_TEMP_DIR = Path(tempfile.mkdtemp(prefix="kissaten_test_db_"))
os.environ["KISSATEN_DATABASE_PATH"] = str(_TEMP_DIR / "kissaten_test.duckdb")
# Permissive DuckDB config so load_coffee_data (read_json/glob) works.
os.environ["KISSATEN_USE_RW_DB"] = "1"
# The podcast database is opened at import time in podcast_db.py; point it
# at a temp file too so the test run doesn't fight any long-lived dev
# server's read/write lock on ``data/podcasts.duckdb``.
os.environ["KISSATEN_PODCAST_DATABASE_PATH"] = str(
    _TEMP_DIR / "kissaten_podcast_test.duckdb"
)
# Defensive fallback: brew_assistant and podcast_db build a Gemini Agent at
# import time. We construct those agents lazily now, but a developer key
# already in the env wins and any test that touches `agent` directly still
# needs *something* set so pydantic_ai doesn't raise. ``setdefault`` lets
# a real key in a developer's env take precedence; CI gets the fake.
os.environ.setdefault("GOOGLE_API_KEY", "test-fake-key-for-import-only")

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import duckdb  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import kissaten.api.db as _db_module  # noqa: E402
from kissaten.api.db import conn, init_database, load_coffee_data  # noqa: E402

# The AI search agent opens ``data/ai_search_cache.duckdb`` (a relative
# path) at app-startup time. If a long-lived dev server is already holding
# the lock on that file, the test client would fail to start. Redirect the
# default cache path to a temp file before any kissaten import so the
# lifespan handler picks it up.
from kissaten.cache.ai_search_cache import AISearchCache  # noqa: E402

_TEST_AI_CACHE_PATH = _TEMP_DIR / "ai_search_cache_test.duckdb"
_original_cache_init = AISearchCache.__init__


def _patched_cache_init(self, cache_db_path=None):
    if cache_db_path is None or cache_db_path == "data/ai_search_cache.duckdb":
        cache_db_path = _TEST_AI_CACHE_PATH
    _original_cache_init(self, cache_db_path)


AISearchCache.__init__ = _patched_cache_init

from kissaten.api.main import app  # noqa: E402

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
    """Initialise DB schema and load test data once for the whole session.

    The session DB lives at the temp path set above; the developer's real
    ``rw_kissaten.duckdb`` is never touched.
    """
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


@pytest.fixture(scope="session")
def isolated_db_connection():
    """Session-scoped fixture that swaps ``kissaten.api.db.conn`` to a fresh
    DuckDB connection on the session temp file and restores the original on
    teardown. Re-registers UDFs on the new conn so anything that depends on
    them (e.g. ``get_canonical_state``) keeps working.

    Most tests do not need this fixture — the module-level ``conn`` is
    already pointed at the session temp file by ``KISSATEN_DATABASE_PATH``
    and the ``db_session`` fixture populates it once. Use this fixture when
    a test needs a guaranteed-fresh connection (e.g. to drop and recreate
    the database, or to assert connection-level behaviour).
    """
    original = _db_module.conn
    path = os.environ["KISSATEN_DATABASE_PATH"]
    _db_module.conn = duckdb.connect(path)
    _db_module._register_udfs()
    try:
        yield _db_module.conn
    finally:
        try:
            _db_module.conn.close()
        except Exception:
            pass
        _db_module.conn = original


# ---------------------------------------------------------------------------
# Function-scoped fixtures  (run before/after every data-modifying test)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def tmp_roaster_dir():
    """Session-scoped fixture that copies ``test_data/roasters`` into a
    per-session temp directory. Tests that mutate test data (e.g.
    ``test_incremental_updates.py:test_incremental_with_new_file``) should
    use this fixture instead of the source ``test_data/roasters`` to avoid
    contaminating the repo's checked-in test data.
    """
    if not _TEST_DATA_DIR.exists():
        pytest.skip(f"Test data directory not found: {_TEST_DATA_DIR}")
    target = Path(tempfile.mkdtemp(prefix="kissaten_test_roasters_"))
    shutil.copytree(_TEST_DATA_DIR, target / "roasters")
    try:
        yield target / "roasters"
    finally:
        shutil.rmtree(target, ignore_errors=True)


@pytest.fixture
def test_data_dir():
    """Return the shared (read-only) test data directory path."""
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
