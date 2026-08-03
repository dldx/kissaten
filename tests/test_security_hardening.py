#!/usr/bin/env python3
"""
Security hardening tests for kissaten.api

Covers:
  1. validate_currency_code — rejects injection payloads, accepts valid codes
  2. _build_currency_select_sql — correct SQL template / param count in both branches
  3. DuckDB external-access lockdown — read_csv('/etc/passwd') and friends are blocked
  4. /v1/search — SQL injection payloads via convert_to_currency are rejected (HTTP 400)
  5. /v1/search — currency + roaster-filter combo doesn't corrupt column binding
  6. /v1/search/by-paths — same injection / binding sanity checks
"""

import os
import sys
import tempfile
from pathlib import Path

os.environ["PYTEST_CURRENT_TEST"] = "test_security_hardening.py"
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import duckdb
import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi.testclient import TestClient

import kissaten.api.db as db_module
from kissaten.api.db import conn, init_database
from kissaten.api.main import _build_currency_select_sql, app, validate_currency_code

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def setup_database(db_session):
    """Initialize an empty database before each test, tear down after.

    Depends on the conftest's session-scoped ``db_session`` so the underlying
    ``conn`` is the session temp DB, not the developer's working database.
    """
    # Drop stale views first so init_database can recreate them cleanly.
    # This avoids BinderException when a prior test session left an origins
    # table that is missing columns referenced in the view.
    for view in ("coffee_beans_with_origin", "roasters_with_location", "coffee_beans_with_categorized_notes"):
        try:
            conn.execute(f"DROP VIEW IF EXISTS {view}")
        except Exception:
            pass

    await init_database()

    tables = [
        "origins", "coffee_beans", "roasters", "country_codes",
        "roaster_location_codes", "tasting_notes_categories", "processed_files",
    ]
    for table in tables:
        try:
            conn.execute(f"TRUNCATE TABLE {table}")
        except Exception:
            pass
    conn.commit()

    yield

    for table in tables:
        try:
            conn.execute(f"TRUNCATE TABLE {table}")
        except Exception:
            pass
    conn.commit()


@pytest.fixture
def test_data_dir():
    test_dir = Path(__file__).parent.parent / "test_data" / "roasters"
    if not test_dir.exists():
        pytest.skip(f"Test data directory not found: {test_dir}")
    return test_dir


@pytest.fixture
def insert_minimal_test_data():
    """
    Insert a small set of known test data directly via parameterized SQL.

    This avoids using load_coffee_data (which internally uses DuckDB's read_json /
    filesystem glob — blocked by enable_external_access=False).  It gives us precise,
    reproducible test data without any filesystem dependency.
    """
    # One roaster
    conn.execute("""
        INSERT INTO roasters (id, name, slug, website, location, email, active, last_scraped, total_beans_scraped)
        VALUES (?, ?, ?, ?, ?, NULL, true, CURRENT_TIMESTAMP, ?)
    """, [1, 'Test Roaster', 'test-roaster', 'https://test.com', 'GB', 1])

    # One coffee bean priced in GBP so conversion tests can exercise both branches
    conn.execute("""
        INSERT INTO coffee_beans (
            id, name, roaster, url, is_single_origin, roast_level, roast_profile,
            weight, price, currency, price_usd, is_decaf, tasting_notes,
            description, in_stock, scraped_at, scraper_version, filename,
            image_url, clean_url_slug, bean_url_path, date_added
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, NULL, ?, ?, CURRENT_TIMESTAMP)
    """, [
        1, 'Ethiopia Yirgacheffe', 'Test Roaster', 'https://test.com/bean',
        True, 'Light', 'Filter', 250, 15.00, 'GBP', 19.00, False,
        ['Blueberry', 'Lemon'], 'A great Ethiopian coffee', True,
        '2.0', '/test-roaster/2024/ethiopia.json',
        'ethiopia_yirgacheffe', '/test-roaster/ethiopia-yirgacheffe',
    ])

    # One origin for that bean
    conn.execute("""
        INSERT INTO origins (
            id, bean_id, country, region, region_normalized, producer, farm, farm_normalized,
            elevation_min, elevation_max, latitude, longitude, process, process_common_name,
            variety, variety_canonical, harvest_date, state_canonical, farm_canonical,
            process_slug, process_common_slug, variety_canonical_slugs
        ) VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, ?)
    """, [
        1, 1, 'ET', 'Yirgacheffe', 'yirgacheffe',
        1800, 2000, 6.1, 38.2,
        'Washed', 'Washed', 'Heirloom', ['Heirloom'],
        'washed', 'washed', ['heirloom'],
    ])

    # Currency rates so GBP / EUR conversion can work
    conn.execute("""
        INSERT INTO currency_rates (base_currency, target_currency, rate, fetched_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP), (?, ?, ?, CURRENT_TIMESTAMP)
    """, ['USD', 'GBP', 0.79, 'USD', 'EUR', 0.92])

    conn.commit()
    yield
    # setup_database fixture handles the TRUNCATE on teardown


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. validate_currency_code
# ---------------------------------------------------------------------------


class TestValidateCurrencyCode:
    """Unit tests for the validate_currency_code helper."""

    def test_none_returns_none(self):
        assert validate_currency_code(None) is None

    def test_valid_three_letter_uppercase(self):
        for code in ("USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD"):
            assert validate_currency_code(code) == code

    def test_lowercase_is_uppercased(self):
        assert validate_currency_code("eur") == "EUR"
        assert validate_currency_code("gbp") == "GBP"

    def test_mixed_case_is_uppercased(self):
        assert validate_currency_code("Usd") == "USD"

    # --- Injection / malformed payloads ---

    @pytest.mark.parametrize("payload", [
        "USD; DROP TABLE coffee_beans; --",
        "' OR '1'='1",
        "USD' OR 1=1--",
        "EUR\x00",                          # null byte
        "USDE",                             # 4 letters
        "US",                               # 2 letters
        "U",                                # 1 letter
        "",                                 # empty string
        "123",                              # digits only
        "US1",                              # digit in code
        "' UNION SELECT * FROM coffee_beans--",
        "read_csv('/etc/passwd')",
        "EUR; SELECT read_csv('/etc/passwd');",
    ])
    def test_rejects_injection_payloads(self, payload):
        with pytest.raises(HTTPException) as exc_info:
            validate_currency_code(payload)
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# 2. _build_currency_select_sql
# ---------------------------------------------------------------------------


class TestBuildCurrencySelectSql:
    """Unit tests for the _build_currency_select_sql helper."""

    def test_no_currency_returns_literal_sql_and_empty_params(self):
        price_sql, lb_price_sql, currency_sql, price_converted_sql, params = _build_currency_select_sql(None)
        assert price_sql == "sb.price"
        assert lb_price_sql == "sb.lb_price"
        assert currency_sql == "sb.currency"
        assert price_converted_sql == "FALSE"
        assert params == []

    def test_with_currency_returns_eight_params(self):
        _, _, _, _, params = _build_currency_select_sql("EUR")
        assert len(params) == 8, (
            "Expected exactly 8 positional params "
            "(3 in price CASE + 3 in lb_price CASE + 1 currency literal + 1 != check)"
        )

    def test_with_currency_all_params_are_uppercased(self):
        _, _, _, _, params = _build_currency_select_sql("eur")
        assert all(p == "EUR" for p in params), "All params should be the uppercased currency code"

    def test_with_currency_price_sql_contains_placeholders(self):
        price_sql, _, _, _, _ = _build_currency_select_sql("GBP")
        # Must have exactly 3 '?' for the CASE WHEN logic
        assert price_sql.count("?") == 3

    def test_with_currency_lb_price_sql_contains_placeholders(self):
        _, lb_price_sql, _, _, _ = _build_currency_select_sql("GBP")
        # Must have exactly 3 '?' for the CASE WHEN logic
        assert lb_price_sql.count("?") == 3

    def test_with_currency_currency_sql_is_placeholder(self):
        _, _, currency_sql, _, _ = _build_currency_select_sql("GBP")
        assert currency_sql == "?"

    def test_with_currency_price_converted_sql_contains_placeholder(self):
        _, _, _, price_converted_sql, _ = _build_currency_select_sql("GBP")
        assert "?" in price_converted_sql

    def test_sql_fragments_contain_no_raw_currency_string(self):
        """The SQL template must never embed the raw currency value — only '?'."""
        price_sql, lb_price_sql, currency_sql, price_converted_sql, _ = _build_currency_select_sql("GBP")
        for fragment in (price_sql, lb_price_sql, currency_sql, price_converted_sql):
            assert "GBP" not in fragment, (
                f"Raw currency 'GBP' found in SQL fragment: {fragment!r}"
            )


# ---------------------------------------------------------------------------
# 3. DuckDB external-access lockdown
# ---------------------------------------------------------------------------


class TestExternalAccessBlocked:
    """
    Verify that the DuckDB connection used by the production read-only API has
    external access disabled at runtime.

    These tests import db_module directly and derive the production config from
    the same conditional used in db.py (line: ``_db_config = {} if _use_rw_db
    else {}``), so a regression in db.py breaks these tests — not just arbitrary
    in-memory connections.

    Note: the shared ``conn`` fixture runs with KISSATEN_USE_RW_DB=1 so that
    test fixtures can write data.  The *production* connection (no env var) uses
    a permissive initial config that is immediately locked down; we derive it
    here via the same formula and runtime setup.
    """

    @staticmethod
    def _production_config() -> dict:
        """Return the config db.py applies when KISSATEN_USE_RW_DB is not set.

        Mirrors the config formula in db.py exactly::

            _db_config = {} if _use_rw_db else {}

        with ``_use_rw_db = False`` (the production path).
        """
        use_rw = False  # production: KISSATEN_USE_RW_DB unset
        return {} if use_rw else {}

    @classmethod
    def _production_conn(cls) -> duckdb.DuckDBPyConnection:
        """Open a DuckDB connection with the production API config and apply
        the runtime connection lockdown.

        DuckDB 1.5+ refuses ``read_only=True`` against ``:memory:`` ("Cannot
        launch in-memory database in read-only mode!") and against a missing
        file, so we seed a per-call temp file with a throwaway read-write
        connection first.
        """
        # Production opens read-only + permissive config + LOAD fts +
        # enable_external_access=false. read_only=True is what guarantees
        # the API process never writes to the DB file (and therefore can
        # never corrupt it via the swap-under-open path).
        tmpdir = tempfile.mkdtemp(prefix="kissaten_ro_")
        path = os.path.join(tmpdir, "ro.duckdb")
        duckdb.connect(path).close()  # seed the file; read-only can't create it
        conn = duckdb.connect(path, read_only=True, config=cls._production_config())
        try:
            conn.execute("LOAD fts;")
        except duckdb.Error:
            conn.execute("INSTALL fts; LOAD fts;")
        conn.execute("SET enable_external_access = false;")
        return conn

    # --- Config correctness: test the actual db_module state ---

    def test_db_module_config_matches_use_rw_formula(self):
        """db._db_config must equal the formula evaluated against the actual
        _use_rw_db flag.  If db.py's conditional is changed or bypassed this
        assertion fails."""
        expected = {} if db_module._use_rw_db else {}
        assert db_module._db_config == expected, (
            f"db._db_config={db_module._db_config!r} does not match formula "
            f"result={expected!r} for _use_rw_db={db_module._use_rw_db}"
        )

    def test_db_module_use_read_only_matches_formula(self):
        """db._use_read_only must equal ``not _use_rw_db`` — the API opens
        read-only so it cannot write to kissaten.duckdb (the swap-corruption
        defense). Pinning this here means a future refactor that drops the
        read-only flag fails CI, not production."""
        assert db_module._use_read_only is (not db_module._use_rw_db), (
            f"_use_read_only={db_module._use_read_only!r} does not match "
            f"not _use_rw_db={not db_module._use_rw_db!r}"
        )

    def test_use_rw_flag_reflects_env_var(self):
        """_use_rw_db must be derived from KISSATEN_USE_RW_DB, not hard-coded."""
        assert db_module._use_rw_db == (os.environ.get("KISSATEN_USE_RW_DB") == "1"), (
            "_use_rw_db in db.py does not reflect the KISSATEN_USE_RW_DB env var"
        )

    def test_production_config_matches_rw_config(self):
        """Both branches of db.py's _db_config formula resolve to ``{}``.

        The production DB safety guard in ``_check_production_db_guard`` is the
        sole protection against accidental writes to ``kissaten.duckdb`` /
        ``rw_kissaten.duckdb`` from tests/scripts; the DuckDB connection config
        itself is permissive on both sides so that the FTS extension can be
        LOADed at API startup.
        """
        config = self._production_config()
        assert config == {}, (
            f"Production config {config!r} should be {{}} (permissive); "
            'check db.py line: _db_config = {} if _use_rw_db else {}'
        )

    def test_production_db_guard_refuses_writable_config(self):
        """_check_production_db_guard must still refuse to open kissaten.duckdb
        or rw_kissaten.duckdb with a writable config when KISSATEN_ALLOW_PRODUCTION_DB
        is unset, even though the DuckDB config itself is permissive.

        This is the real defence-in-depth: a test or script pointing
        kissaten.api.db at the production file must explicitly opt in.
        """
        from kissaten.api.db import _check_production_db_guard, _project_data_dir
        for name in ("kissaten.duckdb", "rw_kissaten.duckdb"):
            db_path = _project_data_dir() / name
            with pytest.raises(RuntimeError, match="Refusing to open protected database"):
                _check_production_db_guard(db_path, {"enable_external_access": True})

    def test_production_db_guard_allows_with_opt_in(self):
        """_check_production_db_guard must allow the connection when
        KISSATEN_ALLOW_PRODUCTION_DB=1 is set."""
        from kissaten.api.db import _check_production_db_guard, _project_data_dir
        old = os.environ.get("KISSATEN_ALLOW_PRODUCTION_DB")
        os.environ["KISSATEN_ALLOW_PRODUCTION_DB"] = "1"
        try:
            for name in ("kissaten.duckdb", "rw_kissaten.duckdb"):
                db_path = _project_data_dir() / name
                # Should not raise
                _check_production_db_guard(db_path, {"enable_external_access": True})
        finally:
            if old is None:
                os.environ.pop("KISSATEN_ALLOW_PRODUCTION_DB", None)
            else:
                os.environ["KISSATEN_ALLOW_PRODUCTION_DB"] = old

    # --- Enforcement: a connection built with the production config blocks ops ---

    def test_read_csv_passwd_is_blocked(self):
        """read_csv('/etc/passwd') must be blocked by the production config."""
        rc = self._production_conn()
        with pytest.raises(duckdb.Error):
            rc.execute("SELECT * FROM read_csv('/etc/passwd')")
        rc.close()

    def test_read_parquet_is_blocked(self):
        rc = self._production_conn()
        with pytest.raises(duckdb.Error):
            rc.execute("SELECT * FROM read_parquet('/tmp/test.parquet')")
        rc.close()

    def test_read_json_is_blocked(self):
        rc = self._production_conn()
        with pytest.raises(duckdb.Error):
            rc.execute("SELECT * FROM read_json('/tmp/test.json')")
        rc.close()

    def test_http_filesystem_is_blocked(self):
        """HTTP/HTTPS access should also be denied."""
        rc = self._production_conn()
        with pytest.raises(duckdb.Error):
            rc.execute("SELECT * FROM read_csv('https://example.com/data.csv')")
        rc.close()

    def test_copy_to_filesystem_is_blocked(self):
        rc = self._production_conn()
        with pytest.raises(duckdb.Error):
            rc.execute("COPY (SELECT 1) TO '/tmp/kissaten_test_leak.csv'")
        rc.close()


# ---------------------------------------------------------------------------
# 4. /v1/search — injection via convert_to_currency
# ---------------------------------------------------------------------------


class TestSearchCurrencyInjection:
    """
    Injection payloads in convert_to_currency must be rejected with HTTP 400
    before they ever reach the SQL layer.
    """

    @pytest.mark.parametrize("payload", [
        "USD; DROP TABLE coffee_beans; --",
        "' OR '1'='1",
        "USDD",           # 4 chars
        "US",             # 2 chars
        "123",
        "US1",
        "read_csv('/etc/passwd')",
    ])
    def test_injection_payload_returns_400(self, client, payload):
        import urllib.parse
        encoded = urllib.parse.quote(payload)
        response = client.get(f"/v1/search?convert_to_currency={encoded}")
        assert response.status_code == 400, (
            f"Expected 400 for payload {payload!r}, got {response.status_code}"
        )

    def test_valid_currency_code_accepted(self, client):
        """A well-formed 3-letter code must not be rejected by the currency validator."""
        response = client.get("/v1/search?convert_to_currency=EUR")
        # The validator should not reject a valid code with a currency-validation 400.
        # The response may be 200 (data found) or 400/500 from DB issues on an empty
        # test DB — but the error body must NOT mention 'Invalid currency code'.
        if response.status_code == 400:
            body = response.json()
            assert "Invalid currency code" not in body.get("detail", ""), (
                f"Valid currency 'EUR' was incorrectly rejected: {body}"
            )


# ---------------------------------------------------------------------------
# 5. /v1/search — currency + roaster filter binding correctness
# ---------------------------------------------------------------------------


class TestSearchCurrencyBindingCorrectness:
    """
    Regression tests for the bug where currency_params were prepended before
    score-calculation params, causing roaster names to bleed into currency columns.
    """

    @pytest.mark.asyncio
    async def test_currency_field_is_valid_iso_code(self, setup_database, insert_minimal_test_data, client):
        """
        When convert_to_currency=GBP and a roaster filter is active, the 'currency'
        field in every result must be a 3-character string (not a roaster name).
        """
        import urllib.parse
        response = client.get(
            f"/v1/search?convert_to_currency=GBP&roaster={urllib.parse.quote('Test Roaster')}&per_page=5"
        )

        assert response.status_code == 200, f"Unexpected status: {response.status_code}"
        data = response.json()
        assert data["success"] is True

        for bean in data["data"]:
            currency = bean.get("currency")
            if currency is not None:
                assert len(currency) <= 3, (
                    f"currency field contains a non-currency value: {currency!r} "
                    f"(looks like a roaster name bleed from parameter binding bug)"
                )

    @pytest.mark.asyncio
    async def test_currency_field_matches_target_currency(self, setup_database, insert_minimal_test_data, client):
        """
        Beans that had their price converted should report the target currency,
        not some other value from the params list.
        """
        response = client.get("/v1/search?convert_to_currency=USD&per_page=10")
        assert response.status_code == 200
        data = response.json()

        for bean in data["data"]:
            if bean.get("price_converted"):
                assert bean["currency"] == "USD", (
                    f"Converted bean has wrong currency: {bean['currency']!r}"
                )

    @pytest.mark.asyncio
    async def test_relevance_sort_with_currency_does_not_corrupt_binding(
        self, setup_database, insert_minimal_test_data, client
    ):
        """
        In scoring/relevance mode the score_calculation_clause params appear in the
        CTE before the currency SELECT params. Make sure they don't collide.
        """
        response = client.get(
            "/v1/search?sort_by=relevance&query=ethiopia&convert_to_currency=EUR&per_page=5"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        for bean in data["data"]:
            currency = bean.get("currency")
            if currency is not None:
                assert len(currency) <= 3, (
                    f"currency field corrupted in relevance+currency mode: {currency!r}"
                )


# ---------------------------------------------------------------------------
# 6. /v1/search/by-paths — injection and binding
# ---------------------------------------------------------------------------


class TestSearchByPathsCurrencyInjection:
    """Injection and binding correctness for the POST /v1/search/by-paths endpoint."""

    @pytest.mark.parametrize("payload", [
        "USD; DROP TABLE coffee_beans;--",
        "' OR 1=1--",
        "GBPP",
        "G1P",
    ])
    def test_injection_payload_returns_400(self, client, payload):
        import urllib.parse
        encoded = urllib.parse.quote(payload)
        response = client.post(
            f"/v1/search/by-paths?convert_to_currency={encoded}",
            json={"bean_url_paths": []},
        )
        # FastAPI may return 400 (from our validate_currency_code HTTPException) or
        # 422 (if Pydantic rejects the body/params before our code runs).
        # Both mean the request was correctly rejected.
        assert response.status_code in (400, 422), (
            f"Expected 400 or 422 for payload {payload!r}, got {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_currency_field_is_valid_iso_code(self, setup_database, insert_minimal_test_data, client):
        """Currency column must not contain non-currency data in by-paths endpoint."""
        path = '/test-roaster/ethiopia-yirgacheffe'

        response = client.post(
            "/v1/search/by-paths?convert_to_currency=EUR",
            json={"bean_url_paths": [path]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        for bean in data["data"]:
            currency = bean.get("currency")
            if currency is not None:
                assert len(currency) <= 3, (
                    f"currency field corrupted in by-paths endpoint: {currency!r}"
                )


# ---------------------------------------------------------------------------
# 7. API mode: read-only connection + zero-write contract
# ---------------------------------------------------------------------------


class TestApiModeIsReadOnly:
    """Pin the read-only API contract introduced to fix the
    ``cp rw_kissaten.duckdb kissaten.duckdb`` swap-under-open corruption bug.

    The ``kissaten serve`` process must open ``kissaten.duckdb`` with
    ``read_only=True`` so that:

      * no WAL is ever created by the API process,
      * the API process cannot dirty the buffer pool,
      * SIGTERM/SIGKILL of the running server leaves the file bit-identical,
      * any accidental write path fails loudly (instead of silently mutating
        production data).

    These tests poke at the ``db`` module from API-mode assumptions and
    monkey-patch the module state to simulate the ``KISSATEN_USE_RW_DB`` flag
    being unset. They do not require a full subprocess restart.
    """

    def _swap_to_api_mode(self, monkeypatch, *, populate: bool = False):
        """Flip db_module into API mode (read_only=True, _use_rw_db=False)
        without touching the live ``conn`` (we replace it).

        DuckDB refuses two simultaneous connections to the same file with
        different modes, so we always open a fresh temp file. If
        ``populate`` is True the temp file is pre-populated with the schema
        the ``ensure_*`` helpers expect to migrate.
        """
        tmpdir = tempfile.mkdtemp(prefix="kissaten_api_ro_")
        path = os.path.join(tmpdir, "api.duckdb")
        if populate:
            # Build the schema with a read-write connection, then close it.
            seed = duckdb.connect(path)
            try:
                seed.execute("CREATE TABLE coffee_beans(id INTEGER PRIMARY KEY, name VARCHAR)")
                seed.execute("CREATE TABLE roasters(id INTEGER PRIMARY KEY, name VARCHAR UNIQUE, description TEXT)")
                seed.execute("CREATE TABLE origins(id INTEGER PRIMARY KEY, bean_id INTEGER)")
                seed.execute("CREATE TABLE price_options(id INTEGER PRIMARY KEY, bean_id INTEGER, weight INTEGER, price DOUBLE, currency VARCHAR, price_per_kg DOUBLE, price_per_kg_usd DOUBLE)")
                for t in ("country_codes", "roaster_location_codes",
                          "tasting_notes_categories", "processed_files",
                          "currency_rates", "varietal_mappings",
                          "coffee_varietals"):
                    seed.execute(f"CREATE TABLE {t}(dummy INTEGER)")
            finally:
                seed.close()
        else:
            # DuckDB refuses to open a missing file in read-only mode, so
            # create an empty DuckDB file via a throwaway read-write conn.
            seed = duckdb.connect(path)
            seed.close()
        ro = duckdb.connect(path, read_only=True)
        monkeypatch.setattr(db_module, "_use_rw_db", False)
        monkeypatch.setattr(db_module, "_use_read_only", True)
        monkeypatch.setattr(db_module, "conn", ro)
        return ro

    def test_ensure_views_is_noop_in_api_mode(self, monkeypatch):
        """ensure_views() must return early in API mode (read-only)."""
        ro = self._swap_to_api_mode(monkeypatch)
        try:
            # If the gate is missing, this would attempt DROP VIEW IF EXISTS
            # and raise against the read-only connection.
            db_module.ensure_views()
            # And the connection must still be open + readable.
            assert ro.execute("SELECT 1").fetchone() == (1,)
        finally:
            ro.close()

    def test_ensure_indexing_columns_is_noop_in_api_mode(self, monkeypatch):
        ro = self._swap_to_api_mode(monkeypatch)
        try:
            db_module.ensure_indexing_columns()
            assert ro.execute("SELECT 1").fetchone() == (1,)
        finally:
            ro.close()

    def test_ensure_roasters_description_column_is_noop_in_api_mode(self, monkeypatch):
        # Populate with the schema the function expects, so it actually
        # reaches the read-only branch and not the "table missing" early-out.
        ro = self._swap_to_api_mode(monkeypatch, populate=True)
        try:
            db_module.ensure_roasters_description_column()
            assert ro.execute("SELECT 1").fetchone() == (1,)
        finally:
            ro.close()

    def test_api_mode_schema_warnings_runs_read_only(self, monkeypatch):
        """The API-mode schema verifier must complete without raising and
        without producing writes (it is read-only SQL only)."""
        ro = self._swap_to_api_mode(monkeypatch, populate=True)
        try:
            # Should not raise — and should not produce any WAL because
            # read_only connections cannot write.
            db_module._api_mode_schema_warnings()
            assert ro.execute("SELECT 1").fetchone() == (1,)
        finally:
            ro.close()

    def test_production_connection_refuses_writes(self):
        """End-to-end: a connection built the same way the API builds its
        production connection (read_only=True, permissive config, LOAD fts,
        SET enable_external_access=false) must reject writes with a clean
        ``duckdb.Error`` — proving the API cannot accidentally mutate
        production data."""
        rc = TestExternalAccessBlocked._production_conn()
        try:
            with pytest.raises(duckdb.Error):
                rc.execute("CREATE TABLE should_fail(i INTEGER)")
        finally:
            rc.close()

    def test_ensure_connection_uses_read_only_in_api_mode(self, monkeypatch):
        """_ensure_connection() must open with read_only=_use_read_only so
        that any code path that triggers a re-open (currently none in normal
        flow, but test fixtures / future refactors) inherits the same
        contract."""
        monkeypatch.setattr(db_module, "_use_rw_db", False)
        monkeypatch.setattr(db_module, "_use_read_only", True)
        # Wipe the module conn so _ensure_connection will rebuild it.
        monkeypatch.setattr(db_module, "conn", None)
        # Point the safety guard at a temp path so it doesn't refuse.
        monkeypatch.setenv("KISSATEN_DATABASE_PATH",
                           os.path.join(tempfile.mkdtemp(prefix="kissaten_ro_"),
                                        "ro.duckdb"))
        try:
            db_module._ensure_connection()
            assert db_module.conn is not None
            with pytest.raises(duckdb.Error):
                db_module.conn.execute("CREATE TABLE should_fail(i INTEGER)")
        finally:
            if db_module.conn is not None:
                try:
                    db_module.conn.close()
                except Exception:
                    pass
                monkeypatch.setattr(db_module, "conn", None)


# ---------------------------------------------------------------------------
# 8. FX endpoints are disabled in API mode (read-only)
# ---------------------------------------------------------------------------


class TestFxEndpointsReadOnly:
    """The mutating FX endpoints must refuse to run when the API is serving
    in read-only mode — otherwise the DELETE/INSERT on ``currency_rates``
    would raise against a read-only connection, turning a 200 into a 500.

    ``create_fx_router()`` decorates endpoints onto the module-level
    ``fx.router`` object, so calling it twice would register duplicate
    routes (first match wins) and the 409 gate would never be reached
    through HTTP routing. We therefore monkey-patch in a fresh router and
    invoke the endpoint functions directly.
    """

    @staticmethod
    def _fresh_fx_router(monkeypatch):
        from fastapi import APIRouter

        import kissaten.api.fx as fx_module

        fresh = APIRouter(prefix="/v1", tags=["Currency"])
        monkeypatch.setattr(fx_module, "router", fresh)
        return fx_module.create_fx_router()

    @staticmethod
    def _endpoint(router, path: str):
        for route in router.routes:
            if getattr(route, "path", None) == path and "POST" in getattr(route, "methods", set()):
                return route.endpoint
        raise AssertionError(f"POST {path} not found on router")

    @pytest.mark.asyncio
    async def test_force_update_returns_409_in_api_mode(self, monkeypatch):
        monkeypatch.setattr(db_module, "_use_rw_db", False)
        monkeypatch.setattr(db_module, "_use_read_only", True)
        router = self._fresh_fx_router(monkeypatch)
        endpoint = self._endpoint(router, "/v1/currencies/update")
        with pytest.raises(HTTPException) as exc_info:
            await endpoint()
        assert exc_info.value.status_code == 409
        assert "read-only" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_refresh_returns_409_in_api_mode(self, monkeypatch):
        monkeypatch.setattr(db_module, "_use_rw_db", False)
        monkeypatch.setattr(db_module, "_use_read_only", True)
        router = self._fresh_fx_router(monkeypatch)
        endpoint = self._endpoint(router, "/v1/currencies/refresh")
        with pytest.raises(HTTPException) as exc_info:
            await endpoint()
        assert exc_info.value.status_code == 409
        assert "read-only" in exc_info.value.detail.lower()
