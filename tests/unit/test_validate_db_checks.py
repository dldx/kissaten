"""Unit tests for the validate-db in-stock drift (G) and batch health (H) checks.

These gates exist so a scraping outage (e.g. the 2026-07-27/28 proxy failure)
can no longer result in a poisoned rw DB passing validation and being
promoted to production.
"""

import json
from datetime import datetime, timedelta, timezone

import duckdb

from kissaten.cli.main import _check_batch_health, _check_instock_drift


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
