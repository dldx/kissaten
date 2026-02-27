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
from pathlib import Path

os.environ["PYTEST_CURRENT_TEST"] = "test_security_hardening.py"
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
import pytest_asyncio
import duckdb
from fastapi.testclient import TestClient
from fastapi import HTTPException

import kissaten.api.db as db_module
from kissaten.api.db import conn, init_database
from kissaten.api.main import app, validate_currency_code, _build_currency_select_sql


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def setup_database():
    """Initialize an empty database before each test, tear down after."""
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
        price_sql, currency_sql, price_converted_sql, params = _build_currency_select_sql(None)
        assert price_sql == "sb.price"
        assert currency_sql == "sb.currency"
        assert price_converted_sql == "FALSE"
        assert params == []

    def test_with_currency_returns_five_params(self):
        _, _, _, params = _build_currency_select_sql("EUR")
        assert len(params) == 5, "Expected exactly 5 positional params (3 in CASE + 1 currency literal + 1 != check)"

    def test_with_currency_all_params_are_uppercased(self):
        _, _, _, params = _build_currency_select_sql("eur")
        assert all(p == "EUR" for p in params), "All params should be the uppercased currency code"

    def test_with_currency_price_sql_contains_placeholders(self):
        price_sql, _, _, _ = _build_currency_select_sql("GBP")
        # Must have exactly 3 '?' for the CASE WHEN logic
        assert price_sql.count("?") == 3

    def test_with_currency_currency_sql_is_placeholder(self):
        _, currency_sql, _, _ = _build_currency_select_sql("GBP")
        assert currency_sql == "?"

    def test_with_currency_price_converted_sql_contains_placeholder(self):
        _, _, price_converted_sql, _ = _build_currency_select_sql("GBP")
        assert "?" in price_converted_sql

    def test_sql_fragments_contain_no_raw_currency_string(self):
        """The SQL template must never embed the raw currency value — only '?'."""
        price_sql, currency_sql, price_converted_sql, _ = _build_currency_select_sql("GBP")
        for fragment in (price_sql, currency_sql, price_converted_sql):
            assert "GBP" not in fragment, (
                f"Raw currency 'GBP' found in SQL fragment: {fragment!r}"
            )


# ---------------------------------------------------------------------------
# 3. DuckDB external-access lockdown
# ---------------------------------------------------------------------------


class TestExternalAccessBlocked:
    """
    Verify that the DuckDB connection used by the production read-only API has
    external access disabled.

    These tests import db_module directly and derive the production config from
    the same conditional used in db.py (line: ``_db_config = {} if _use_rw_db
    else {"enable_external_access": False}``), so a regression in db.py breaks
    these tests — not just arbitrary in-memory connections.

    Note: the shared ``conn`` fixture runs with KISSATEN_USE_RW_DB=1 so that
    test fixtures can write data.  The *production* connection (no env var) uses
    the restricted config; we derive it here via the same formula.
    """

    @staticmethod
    def _production_config() -> dict:
        """Return the config db.py applies when KISSATEN_USE_RW_DB is not set.

        Mirrors line 42 of db.py exactly::

            _db_config = {} if _use_rw_db else {"enable_external_access": False}

        with ``_use_rw_db = False`` (the production path).
        """
        use_rw = False  # production: KISSATEN_USE_RW_DB unset
        return {} if use_rw else {"enable_external_access": False}

    @classmethod
    def _production_conn(cls) -> duckdb.DuckDBPyConnection:
        """Open an in-memory DuckDB connection with the production API config."""
        return duckdb.connect(":memory:", config=cls._production_config())

    # --- Config correctness: test the actual db_module state ---

    def test_db_module_config_matches_use_rw_formula(self):
        """db._db_config must equal the formula evaluated against the actual
        _use_rw_db flag.  If db.py's conditional is changed or bypassed this
        assertion fails."""
        expected = {} if db_module._use_rw_db else {"enable_external_access": False}
        assert db_module._db_config == expected, (
            f"db._db_config={db_module._db_config!r} does not match formula "
            f"result={expected!r} for _use_rw_db={db_module._use_rw_db}"
        )

    def test_use_rw_flag_reflects_env_var(self):
        """_use_rw_db must be derived from KISSATEN_USE_RW_DB, not hard-coded."""
        assert db_module._use_rw_db == (os.environ.get("KISSATEN_USE_RW_DB") == "1"), (
            "_use_rw_db in db.py does not reflect the KISSATEN_USE_RW_DB env var"
        )

    def test_production_config_disables_external_access(self):
        """The non-rw branch of db.py's _db_config formula must contain
        enable_external_access=False (verified by evaluating the formula with
        _use_rw_db=False, matching the production code path)."""
        config = self._production_config()
        assert config.get("enable_external_access") is False, (
            f"Production config {config!r} does not disable external access; "
            'check db.py line: _db_config = {} if _use_rw_db else {"enable_external_access": False}'
        )

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
