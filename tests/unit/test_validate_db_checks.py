"""Unit tests for the validate-db in-stock drift (G) and batch health (H) checks.

These gates exist so a scraping outage (e.g. the 2026-07-27/28 proxy failure)
can no longer result in a poisoned rw DB passing validation and being
promoted to production.
"""

import json
from datetime import datetime, timedelta, timezone

import duckdb

from kissaten.cli.main import (
    _check_batch_health,
    _check_fts_index,
    _check_fts_index_tables,
    _check_fts_match_probe,
    _check_instock_drift,
)


def _make_beans_db(roaster_stock: dict[str, int]):
    """In-memory DuckDB with a minimal coffee_beans table.

    Args:
        roaster_stock: roaster name -> number of in-stock beans.
    """
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE coffee_beans (id INTEGER, roaster VARCHAR, in_stock BOOLEAN)")
    rows = []
    bean_id = 0
    for roaster, count in roaster_stock.items():
        for _ in range(count):
            bean_id += 1
            rows.append((bean_id, roaster, True))
    if rows:
        con.executemany("INSERT INTO coffee_beans VALUES (?, ?, ?)", rows)
    return con


def _snapshot(in_stock_beans: int, by_roaster: dict[str, int]) -> dict:
    return {"counts": {"in_stock_beans": in_stock_beans, "in_stock_by_roaster": by_roaster}}


class TestInstockDrift:
    def test_no_snapshot_passes(self):
        con = _make_beans_db({"Roaster A": 10})
        result = _check_instock_drift(con, None)
        assert result.passed

    def test_old_snapshot_without_instock_baseline_passes(self):
        con = _make_beans_db({"Roaster A": 10})
        result = _check_instock_drift(con, {"counts": {"coffee_beans": 10}})
        assert result.passed
        assert "no in-stock baseline" in result.message.lower() or "baseline" in result.message

    def test_small_drift_passes(self):
        con = _make_beans_db({"Roaster A": 45, "Roaster B": 45})
        result = _check_instock_drift(con, _snapshot(100, {"Roaster A": 50, "Roaster B": 50}))
        assert result.passed

    def test_large_global_drop_fails(self):
        con = _make_beans_db({"Roaster A": 30, "Roaster B": 30})
        result = _check_instock_drift(con, _snapshot(100, {"Roaster A": 50, "Roaster B": 50}))
        assert not result.passed
        assert "in_stock" in result.message

    def test_per_roaster_wipeout_fails(self):
        # Global drop is only 15% (below the 30% tolerance) but Roaster A
        # went from 15 in-stock beans to 0 — the outage failure signature.
        con = _make_beans_db({"Roaster B": 85})
        result = _check_instock_drift(con, _snapshot(100, {"Roaster A": 15, "Roaster B": 85}))
        assert not result.passed
        assert "Roaster A" in result.message

    def test_small_roaster_wipeout_passes(self):
        # Roasters below the wipeout floor (10 in-stock beans) are ignored.
        con = _make_beans_db({"Roaster B": 95})
        result = _check_instock_drift(con, _snapshot(100, {"Roaster A": 5, "Roaster B": 95}))
        assert result.passed

    def test_new_roaster_not_in_snapshot_ignored(self):
        con = _make_beans_db({"Roaster A": 50, "Roaster B": 45, "Roaster C": 20})
        result = _check_instock_drift(con, _snapshot(100, {"Roaster A": 50, "Roaster B": 50}))
        assert result.passed


def _write_batch_results(path, *, failed: int, total: int, beans: int, age_hours: float = 0.0):
    finished_at = datetime.now(timezone.utc) - timedelta(hours=age_hours)
    scrapers = [
        {"name": f"scraper_{i}", "roaster": f"Roaster {i}", "outcome": "success" if i >= failed else "failed",
         "beans_found": beans // total if total else 0}
        for i in range(total)
    ]
    payload = {
        "finished_at": finished_at.isoformat(),
        "total_scrapers": total,
        "successful_count": total - failed,
        "failed_count": failed,
        "skipped_count": 0,
        "scrapers": scrapers,
    }
    path.write_text(json.dumps(payload))
    return path


class TestBatchHealth:
    def test_missing_file_passes(self, tmp_path):
        result = _check_batch_health(None, tmp_path / "does_not_exist.json")
        assert result.passed

    def test_unreadable_file_passes(self, tmp_path):
        path = tmp_path / "last_batch_results.json"
        path.write_text("{not json")
        result = _check_batch_health(None, path)
        assert result.passed

    def test_healthy_batch_passes(self, tmp_path):
        path = _write_batch_results(tmp_path / "b.json", failed=2, total=14, beans=140)
        result = _check_batch_health(None, path)
        assert result.passed

    def test_mass_failure_fails(self, tmp_path):
        # The 2026-07-27/28 outage signature: 13/14 scrapers failed.
        path = _write_batch_results(tmp_path / "b.json", failed=13, total=14, beans=140)
        result = _check_batch_health(None, path)
        assert not result.passed
        assert "13/14" in result.message

    def test_zero_beans_fails(self, tmp_path):
        path = _write_batch_results(tmp_path / "b.json", failed=1, total=14, beans=0)
        result = _check_batch_health(None, path)
        assert not result.passed
        assert "0 beans" in result.message

    def test_stale_results_skip_gate(self, tmp_path):
        # A mass failure older than the max age must not deadlock validation
        # when scraping is paused.
        path = _write_batch_results(tmp_path / "b.json", failed=14, total=14, beans=0, age_hours=48)
        result = _check_batch_health(None, path)
        assert result.passed
        assert "old" in result.message

    def test_exactly_half_failed_fails(self, tmp_path):
        path = _write_batch_results(tmp_path / "b.json", failed=7, total=14, beans=70)
        result = _check_batch_health(None, path)
        assert not result.passed


def _make_fts_db(*, beans: int = 3, with_index: bool = True, fts_source_rows: int | None = None):
    """Build an in-memory DuckDB with a minimal coffee_beans table and
    coffee_beans_fts_source so the validate-db FTS sub-checks have something
    to inspect.

    Args:
        beans: number of coffee_beans rows to create.
        with_index: whether to PRAGMA create_fts_index on the source table
            (mirrors a healthy refresh).
        fts_source_rows: override the fts_source row count. When None, the
            source table mirrors beans; pass ``0`` to emulate the regression
            where ensure_fts_index ran on empty tables.
    """
    con = duckdb.connect(":memory:")
    con.execute("LOAD fts;")
    con.execute(
        "CREATE TABLE coffee_beans ("
        "id INTEGER PRIMARY KEY, name VARCHAR, roaster VARCHAR, url VARCHAR, "
        "scraped_at TIMESTAMP, in_stock BOOLEAN)"
    )
    con.executemany(
        "INSERT INTO coffee_beans VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?)",
        [(i, f"Coffee Bean {i}", "Roaster", "https://example.com", i % 2 == 0) for i in range(1, beans + 1)],
    )

    fts_rows = fts_source_rows if fts_source_rows is not None else beans
    if fts_rows > 0:
        con.execute(
            "CREATE TABLE coffee_beans_fts_source AS "
            "SELECT id, name, roaster FROM coffee_beans"
        )
    else:
        # Empty source table — mirrors ensure_fts_index being called before
        # load_coffee_data populated beans (the 2026-07-30 incident).
        con.execute(
            "CREATE TABLE coffee_beans_fts_source ("
            "id INTEGER, name VARCHAR, roaster VARCHAR)"
        )
    if fts_rows > 0 and with_index:
        con.execute(
            "PRAGMA create_fts_index('coffee_beans_fts_source', 'id', 'name', 'roaster', overwrite=1)"
        )
    return con


class TestFtsSourceDivergence:
    def test_healthy_db_passes(self):
        con = _make_fts_db(beans=10)
        result = _check_fts_index(con)
        assert result.passed
        assert result.name == "fts_vs_coffee_beans"

    def test_empty_fts_source_fails(self):
        # Today's regression: beans populated, fts_source empty.
        con = _make_fts_db(beans=9665, fts_source_rows=0)
        result = _check_fts_index(con)
        assert not result.passed
        assert "diverges" in result.message.lower()


class TestFtsIndexTables:
    def test_healthy_db_passes(self):
        con = _make_fts_db(beans=10)
        result = _check_fts_index_tables(con)
        assert result.passed
        assert "docs=" in result.actual

    def test_missing_index_tables_fails(self):
        # fts_source populated but the PRAGMA never ran (no docs/terms
        # tables in the fts_main_* schema) — the subtler failure mode F1
        # alone cannot see.
        con = _make_fts_db(beans=10, with_index=False)
        result = _check_fts_index_tables(con)
        assert not result.passed
        assert "missing_tables" in result.actual
        assert "FTS index artifacts are missing" in result.message

    def test_empty_docs_table_fails(self):
        # fts_source empty (the regression) → index-artifacts check fails
        # independently of the source-count check.
        con = _make_fts_db(beans=10, fts_source_rows=0)
        result = _check_fts_index_tables(con)
        assert not result.passed


class TestFtsMatchProbe:
    def test_healthy_db_passes(self):
        con = _make_fts_db(beans=10)
        result = _check_fts_match_probe(con)
        assert result.passed
        assert "hits=" in result.actual
        assert int(result.actual.split("hits=")[1]) >= 1

    def test_empty_fts_source_returns_zero_hits_or_undefined(self):
        # The exact user-facing symptom: with no FTS index, match_bm25 is
        # undefined (CatalogException) — surfaced as a check failure either
        # way so a broken refresh is never silently promoted.
        con = _make_fts_db(beans=10, fts_source_rows=0)
        result = _check_fts_match_probe(con)
        assert not result.passed
        msg = result.message.lower()
        assert (
            "match_bm25 raised" in msg
            or "zero" in msg
            or "0 hit" in msg
        )

    def test_missing_index_tables_causes_failure(self):
        # No FTS index artifacts at all → match_bm25 is undefined → check
        # surfaces the failure rather than silently passing.
        con = _make_fts_db(beans=10, with_index=False, fts_source_rows=10)
        result = _check_fts_match_probe(con)
        assert not result.passed
