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

## Fixtures & Infrastructure

### conftest.py

All shared fixtures live in `tests/conftest.py`. Key design decisions:

1.  **`KISSATEN_USE_RW_DB=1`** must be set before any kissaten import. The `conftest.py` does this at the top of the file, before importing any kissaten modules. This tells `db.py` to use `data/rw_kissaten.duckdb` (a read-write copy) instead of the production database.

2.  **Session-scoped `db_session` fixture**: Initialises the DB schema and loads test data from `test_data/roasters/` once per session. All tests share this data.

3.  **Session-scoped `client` fixture**: Creates a `TestClient(app)` context manager that depends on `db_session`. The context manager ensures the FastAPI lifespan runs (registering FX/AI search routers). The client is shared across all tests.

4.  **Function-scoped `setup_database` fixture**: For data-modifying tests only. Truncates all tables before the test and reloads the shared dataset after. This restores session state for subsequent read-only tests.

### Test Data

- Location: `test_data/roasters/`
- Contains a curated subset of scraped data (19 beans from multiple roasters)
- Provides coverage for multiple countries (ET, PA, BR, CO, RW, TZ, etc.) with geocoded regions
- Includes cases where multiple raw regions map to the same canonical state (essential for canonical slug testing)

### Fixture Usage Patterns

**Read-only tests** (most common): Use `client` directly:
```python
@pytest.mark.asyncio
async def test_something(client):
    response = client.get("/v1/origins")
    assert response.status_code == 200
```

**Direct DB queries** (for validation logic): Use `db_session` or the `conn` import:
```python
from kissaten.api.db import conn

@pytest.mark.asyncio
async def test_db_check(db_session):
    rows = conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()
    assert rows[0] > 0
```

**Data-modifying tests**: Use `setup_database`:
```python
@pytest.mark.asyncio
async def test_data_modification(setup_database):
    # DB is empty here — insert test data as needed
    ...
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
| `test_ai_search_cache.py` | AI search cache tests |
| `test_proxy_configuration.py` | Proxy configuration tests |
| `test_security_hardening.py` | Security hardening tests |

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
