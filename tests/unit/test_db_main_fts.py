"""Unit tests pinning the FTS index rebuild behaviour of `kissaten.api.db.main`.

Regression coverage: the final `ensure_fts_index()` used to be guarded by
`if not (incremental and refresh_mappings):`, which wrongly skipped the FTS
rebuild when both flags were set even though data *is* loaded in that mode.
The mappings-only mode (`refresh_mappings=True, incremental=False`) returns
early before any data ingestion and must never rebuild the FTS index.

These tests use mocks only and never touch a real database.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from kissaten.api import db, fx


@pytest.fixture
def mock_db_pipeline(monkeypatch):
    """Patch the db/fx module-level names `main` depends on.

    Returns a dict tracking call counts per patched name. `db.conn` is a
    MagicMock so `conn.close()` is a no-op and the shared test connection is
    left untouched.
    """
    calls = {}

    def _counter(name):
        def _record(*args, **kwargs):
            calls[name] = calls.get(name, 0) + 1

        return _record

    monkeypatch.setattr(db, "conn", MagicMock())
    monkeypatch.setattr(fx, "update_currency_rates", AsyncMock())
    monkeypatch.setattr(db, "_ensure_connection", _counter("_ensure_connection"))
    monkeypatch.setattr(db, "_register_udfs", _counter("_register_udfs"))
    monkeypatch.setattr(db, "init_database", AsyncMock(side_effect=_counter("init_database")))
    monkeypatch.setattr(db, "load_coffee_data", AsyncMock(side_effect=_counter("load_coffee_data")))
    monkeypatch.setattr(
        db, "refresh_canonical_data", AsyncMock(side_effect=_counter("refresh_canonical_data"))
    )
    monkeypatch.setattr(
        db, "load_tasting_notes_categories", AsyncMock(side_effect=_counter("load_tasting_notes_categories"))
    )
    monkeypatch.setattr(db, "ensure_fts_index", _counter("ensure_fts_index"))

    return calls


async def test_incremental_refresh_mappings_rebuilds_fts(mock_db_pipeline):
    """Regression case: `--incremental --refresh-mappings` must rebuild FTS.

    Data is loaded in this mode (new beans in addition to canonical column
    refreshes), so the FTS source must be rebuilt exactly once.
    """
    await db.main(incremental=True, refresh_mappings=True)

    assert mock_db_pipeline["ensure_fts_index"] == 1
    assert mock_db_pipeline["load_coffee_data"] == 1
    assert mock_db_pipeline["init_database"] == 1


async def test_incremental_without_mappings_rebuilds_fts(mock_db_pipeline):
    """`--incremental` (no mappings) still loads data and rebuilds FTS."""
    await db.main(incremental=True, refresh_mappings=False)

    assert mock_db_pipeline["ensure_fts_index"] == 1


async def test_full_refresh_rebuilds_fts(mock_db_pipeline):
    """A full refresh loads data and rebuilds FTS exactly once."""
    await db.main(incremental=False, refresh_mappings=False)

    assert mock_db_pipeline["ensure_fts_index"] == 1
    assert mock_db_pipeline["load_coffee_data"] == 1


async def test_mappings_only_skips_data_and_fts(mock_db_pipeline):
    """Mappings-only mode returns early: no FTS, no DB init, no data load."""
    await db.main(incremental=False, refresh_mappings=True)

    assert "ensure_fts_index" not in mock_db_pipeline
    assert "init_database" not in mock_db_pipeline
    assert "load_coffee_data" not in mock_db_pipeline
    assert mock_db_pipeline["refresh_canonical_data"] == 1
