# Testing Infrastructure

This document describes the testing infrastructure, conventions, and known issues for the Kissaten test suite.

## Test Runner

Tests are run with pytest via uv:

```bash
# Run all tests
uv run pytest -v

# Run specific test file
uv run pytest tests/test_canonical_slug_grouping.py -v

# Run multiple related test files
uv run pytest tests/test_origin_hierarchy_counts.py tests/test_region_name_consistency.py tests/test_canonical_slug_grouping.py -v

# Run tests matching a name pattern
uv run pytest -k "test_region" -v

# Run with coverage
uv run pytest --cov=src/kissaten --cov-report=html
```

## Database Isolation

The test suite **never touches the developer's working databases**. The conftest redirects the module-level `kissaten.api.db.conn` to a per-session temp DuckDB file under `/tmp/kissaten_test_db_<rand>/kissaten_test.duckdb`. A safety guard in `src/kissaten/api/db.py` prevents any code path (test, script, or accident) from opening the real `data/rw_kissaten.duckdb` or `data/kissaten.duckdb` with a writable connection config.

### How it works

1. `tests/conftest.py` runs at pytest collection time and sets two env vars **before** any `kissaten` import:
   - `KISSATEN_DATABASE_PATH=<tmp>/kissaten_test.duckdb` — redirects the conn
   - `KISSATEN_USE_RW_DB=1` — selects the permissive DuckDB config (`{}`) that `load_coffee_data` needs for its `read_json` / filesystem glob operations
2. `kissaten.api.db` reads the env vars at module-load time and opens a connection to the temp file. The safety guard sees a non-protected path, so it does not fire.
3. The session-scoped `db_session` fixture calls `init_database()` and `load_coffee_data(test_data/roasters)` against the temp conn once per session.
4. Tests run against the temp conn. The developer's real `rw_kissaten.duckdb` is never opened or modified.

### Why both env vars

- `KISSATEN_DATABASE_PATH` controls *where* the conn points. Setting it to a temp file is what makes the test safe.
- `KISSATEN_USE_RW_DB=1` controls the DuckDB connection *config*. The permissive config (`{}`) is what `load_coffee_data` needs; the restrictive config (`{"enable_external_access": False}`) blocks `read_json` and would break the fixture.

The safety guard was designed so that the *config* must be writable (permissive) **and** the path must be a protected production DB **and** no opt-in env var is set before the guard fires. `kissaten serve` opens `kissaten.duckdb` with the restrictive config and so is unaffected; the test conftest opens a temp file with the permissive config and so is also unaffected.

### Safety guard reference

The guard in `src/kissaten/api/db.py` refuses to open a protected database when **all** of the following are true:

1. The resolved path equals `data/rw_kissaten.duckdb` or `data/kissaten.duckdb` (resolved against the project root, not the cwd).
2. The connection config is the writable form (i.e. `enable_external_access` is not set to `False`).
3. `KISSATEN_ALLOW_PRODUCTION_DB` is not set to `"1"`.

When the guard fires it raises `RuntimeError` whose message includes the offending path, the override env var, and a pointer back to this document.

To open a protected DB anyway (e.g. an ad-hoc debugging script that needs to inspect the working DB), set `KISSATEN_ALLOW_PRODUCTION_DB=1` before importing `kissaten.api.db`. The `kissaten refresh` CLI does this automatically because writing the rw DB is its whole purpose.

## Fixtures

All shared fixtures live in `tests/conftest.py`. The session-scoped fixtures run once per pytest invocation; the function-scoped fixtures run before/after every test that depends on them.

### `db_session` (session-scoped, async)

Initialise the temp DB schema and load test data from `test_data/roasters/` once per session. All tests share this data.

### `client` (session-scoped)

Creates a `TestClient(app)` context manager that depends on `db_session`. The context-manager form runs the FastAPI lifespan (which registers the FX and AI search routers) and only closes the underlying conn at session teardown.

### `isolated_db_connection` (session-scoped)

Swaps `kissaten.api.db.conn` to a fresh `duckdb.connect()` on the session temp file and restores the original on teardown. Re-registers the module UDFs on the swapped conn. Most tests do not need this — the module-level `conn` is already pointed at the temp file by `KISSATEN_DATABASE_PATH` and the `db_session` fixture populates it once. Use this fixture when a test needs a guaranteed-fresh connection (e.g. to drop and recreate the database, or to assert connection-level behaviour).

### `tmp_roaster_dir` (session-scoped)

Copies `test_data/roasters/` into a per-session temp directory. Tests that mutate test data (e.g. `test_incremental_updates.py:test_incremental_with_new_file`) should use this fixture instead of the source `test_data/roasters/` to avoid contaminating the repo's checked-in test data.

### `test_data_dir` (function-scoped)

Returns the shared (read-only) test data directory path.

### `setup_database` (function-scoped, async)

For data-modifying tests. Truncates all tables before the test and reloads the shared dataset after. This restores session state for subsequent read-only tests.

## Test Data

- Location: `test_data/roasters/`
- Contains a curated subset of scraped data (35 JSON files across multiple roasters)
- Provides coverage for multiple countries (ET, PA, BR, CO, RW, TZ, etc.) with geocoded regions
- Includes cases where multiple raw regions map to the same canonical state (essential for canonical slug testing)

## Fixture Usage Patterns

**Read-only tests** (most common): use `client` directly:

```python
@pytest.mark.asyncio
async def test_something(client):
    response = client.get("/v1/origins")
    assert response.status_code == 200
```

**Direct DB queries** (for validation logic): use `db_session` or the `conn` import:

```python
from kissaten.api.db import conn

@pytest.mark.asyncio
async def test_db_check(db_session):
    rows = conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()
    assert rows[0] > 0
```

**Data-modifying tests**: use `setup_database`:

```python
@pytest.mark.asyncio
async def test_data_modification(setup_database):
    # DB is empty here — insert test data as needed
    ...
```

**Tests that mutate test data**: use `tmp_roaster_dir`:

```python
async def test_incremental_with_new_file(setup_database, tmp_roaster_dir):
    new_file = tmp_roaster_dir / "test_roaster_1" / "20250103" / "brand_new.json"
    new_file.write_text(...)
    # test
```

## Test Categories

### Origin Endpoint Tests

| File | Count | Purpose |
|---|---|---|
| `test_region_name_consistency.py` | 7 | Region name display consistency, no duplicates, canonical names |
| `test_origin_hierarchy_counts.py` | 12 | Count consistency across country/region/farm hierarchy |
| `test_canonical_slug_grouping.py` | 7 | COALESCE-based canonical slug grouping correctness |
| `test_origins_api.py` | — | General origin API tests |
| `test_origin_search.py` | — | Origin search functionality |
| `test_invalid_regions.py` | — | Invalid region input handling |
| `test_duplicate_origins.py` | — | Duplicate origin deduplication |
| `test_region_statistics_consistency.py` | — | Region statistics accuracy |

### Other Test Files

| File | Purpose |
|---|---|
| `test_api_misc.py` | Miscellaneous API endpoint tests |
| `test_api_roasters.py` | Roaster-related API tests |
| `test_search_coffee_beans.py` | Bean search functionality |
| `test_tasting_note_categories_search.py` | Tasting note category search |
| `test_tasting_notes_order.py` | Tasting note ordering |
| `test_stock_functionality.py` | In-stock/out-of-stock filtering |
| `test_diff_update_functionality.py` | Incremental data update tests |
| `test_incremental_updates.py` | Incremental database update tests |
| `test_varietal_mappings.py` | Varietal canonicalization tests |
| `test_ai_search_cache.py` | AI search cache tests (uses its own temp cache file) |
| `test_proxy_configuration.py` | Proxy configuration tests |
| `test_security_hardening.py` | Security hardening tests |
| `test_safety_guard.py` | Production-DB safety guard regression tests |
| `tests/unit/` | Pure-unit tests that don't touch the database (scrapers, validators) |

## Known Issues & Gotchas

### DuckDB Lock Conflicts

The most common test failure cause is a DuckDB lock on `data/ai_search_cache.duckdb`. This happens when:
- A previous test run or debug script was killed without cleanup
- The FastAPI lifespan creates an `AISearchAgent` that opens `ai_search_cache.duckdb`
- A stale Python process still holds the lock

**Symptoms**: All tests fail with `ERROR at setup` and:
```
duckdb.duckdb.IOException: IO Error: Could not set lock on file
"data/ai_search_cache.duckdb": Conflicting lock is held in ... (PID XXXXX)
```

**Fix**: Kill the stale process:
```bash
# Find the PID from the error message, then:
kill <PID>

# Or find all Python processes holding DuckDB locks:
lsof data/ai_search_cache.duckdb
```

The same issue applies to `data/podcasts.duckdb` and `data/kissaten.duckdb` if a `kissaten dev` / `kissaten serve` process is still running. Stop the dev server before running the test suite.

### Safety guard failure

If you see:
```
RuntimeError: Refusing to open protected database /home/.../data/rw_kissaten.duckdb
with a writable connection config.
```

it means a test or script tried to open the real working DB. Either:
- The test should be using the conftest's temp DB (most likely cause).
- The script deliberately needs the real DB and should set `KISSATEN_ALLOW_PRODUCTION_DB=1` before importing `kissaten.api.db`.

### Test Isolation

- Read-only tests share the session-scoped database state — they don't modify data.
- The `client` fixture is session-scoped (the `TestClient` lifespan runs once), so the AI search cache connection persists.
- If a test modifies data without using `setup_database`, subsequent tests may see stale state.

### Async Test Markers

All tests that use the `client` or `db_session` fixtures need `@pytest.mark.asyncio` even if the test body is synchronous. This is because the fixtures are async.

The `pyproject.toml` sets `asyncio_mode = "auto"`, which automatically applies the async marker to all async test functions. However, explicitly marking tests is recommended for clarity.

## Writing New Tests

### For New Origin Endpoints

When adding or modifying origin endpoints, add tests that verify:

1.  **Count consistency** between list and detail views (bean_count, farm_count, roaster_count)
2.  **Name consistency** — display names must match between list and detail
3.  **Slug round-trip** — `normalize_region_name(display_name)` → slug → detail returns same name
4.  **No data leaks** — sub-queries in detail endpoints must filter by the correct region/farm
5.  **Canonical grouping** — if geocoded, raw slug variants must merge and not appear independently

### Helper Patterns

Common helpers used across test files:

```python
from kissaten.api.db import conn, normalize_region_name

def _get_countries_with_regions() -> list[str]:
    """Return country codes that have at least one non-empty region."""
    rows = conn.execute("""
        SELECT DISTINCT o.country FROM origins o
        WHERE o.region IS NOT NULL AND o.region != ''
        ORDER BY o.country
    """).fetchall()
    return [r[0] for r in rows]

def _get_geocoded_countries() -> list[str]:
    """Return country codes with at least one geocoded region."""
    rows = conn.execute("""
        SELECT DISTINCT o.country FROM origins o
        WHERE o.state_canonical IS NOT NULL
        ORDER BY o.country
    """).fetchall()
    return [r[0] for r in rows]
```

### Test Naming Conventions

- `test_<what>_matches_<what>` — consistency checks between two views
- `test_<what>_has_no_<problem>` — absence-of-defect checks
- `test_<what>_returns_<expectation>` — positive behavior checks
- `test_no_<problem>` — negative behavior checks (no leaks, no inflation)
