"""Unit tests for the ``kissaten apply-review-decisions`` CLI logic.

Exercises the command directly (plain function call, keyword args) against a
temp frontend SQLite database and a temp data dir — never touching ``data/``.

Approved decisions write a ``.review.diffjson`` (requires_review: false) under
``data/reviews/<YYYY-MM-DD>/``; rejected decisions write nothing; rows with no
matching bean JSON are skipped and stay ``new``. Everything is idempotent.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from kissaten.cli.main import _review_diffjson_filename, apply_review_decisions

ROASTER = "TestRoaster"
BEAN_SLUG = "some_bean"
BEAN_URL = "https://roasters.example.com/products/some-bean"
BEAN_ENTITY_PATH = f"/{ROASTER}/{BEAN_SLUG}"


def _create_frontend_db(path: Path, rows: list[tuple]):
    """Create a page_feedback table and insert the given product-review rows.

    Each row tuple is ``(id, entity_url_path, fields_json, status)``.
    """
    con = sqlite3.connect(path)
    con.execute(
        """
        CREATE TABLE page_feedback (
            id TEXT PRIMARY KEY,
            kind TEXT,
            entity_url_path TEXT,
            entity_name TEXT,
            entity_slug TEXT,
            fields TEXT,
            status TEXT,
            created_at INTEGER,
            updated_at INTEGER
        )
        """
    )
    for row_id, entity_url_path, fields, status in rows:
        con.execute(
            "INSERT INTO page_feedback (id, kind, entity_url_path, entity_slug, fields, status, created_at) "
            "VALUES (?, 'product-review', ?, ?, ?, ?, ?)",
            (row_id, entity_url_path, entity_url_path.split("/")[-1], fields, status, 0),
        )
    con.commit()
    con.close()


def _write_bean_json(data_dir: Path):
    """Write a fake roaster bean JSON matching the CLI's lookup conventions."""
    bean_dir = data_dir / "roasters" / ROASTER / "20260101"
    bean_dir.mkdir(parents=True, exist_ok=True)
    with open(bean_dir / f"{BEAN_SLUG}_120000.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "name": "Some Bean",
                "roaster": ROASTER,
                "url": BEAN_URL,
                "is_tasting_kit": True,
                "requires_review": True,
            },
            f,
        )


@pytest.fixture
def env(tmp_path):
    """Set up a temp frontend DB, a temp data dir with one bean, and return
    the (db_path, data_dir) pair. Each test re-creates its own feedback rows."""
    db_path = tmp_path / "frontend.db"
    data_dir = tmp_path / "data"
    _write_bean_json(data_dir)
    return db_path, data_dir


def _review_diffjson_path(data_dir: Path) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return data_dir / "reviews" / today / f"{_review_diffjson_filename(BEAN_URL)}.review.diffjson"


def _review_files(data_dir: Path) -> list[Path]:
    return list((data_dir / "reviews").glob("**/*.review.diffjson"))


def _status_of(db_path: Path, row_id: str) -> str:
    con = sqlite3.connect(db_path)
    try:
        return con.execute("SELECT status FROM page_feedback WHERE id = ?", (row_id,)).fetchone()[0]
    finally:
        con.close()


class TestDryRun:
    def test_dry_run_writes_nothing_and_keeps_new(self, env):
        db_path, data_dir = env
        _create_frontend_db(
            db_path,
            [("r1", BEAN_ENTITY_PATH, '[{"key": "decision", "value": "approved"}]', "new")],
        )

        apply_review_decisions(from_db=db_path, data_dir=data_dir, dry_run=True, verbose=False)

        assert _review_files(data_dir) == []
        assert _status_of(db_path, "r1") == "new"


class TestApproved:
    def test_writes_diffjson_and_marks_applied(self, env):
        db_path, data_dir = env
        _create_frontend_db(
            db_path,
            [("r1", BEAN_ENTITY_PATH, '[{"key": "decision", "value": "approved"}]', "new")],
        )

        apply_review_decisions(from_db=db_path, data_dir=data_dir, dry_run=False, verbose=False)

        target = _review_diffjson_path(data_dir)
        assert target.exists(), f"expected diffjson at {target}"
        payload = json.loads(target.read_text())
        assert payload["url"] == BEAN_URL
        assert payload["requires_review"] is False
        assert _status_of(db_path, "r1") == "applied"


class TestRejected:
    def test_no_diffjson_but_marks_applied(self, env):
        db_path, data_dir = env
        # Rejected decision needs no matching bean JSON; a unique path avoids
        # colliding with the existing bean.
        _create_frontend_db(
            db_path,
            [("r2", "/TestRoaster/some_rejected", '[{"key": "decision", "value": "rejected"}]', "new")],
        )

        apply_review_decisions(from_db=db_path, data_dir=data_dir, dry_run=False, verbose=False)

        assert _review_files(data_dir) == []
        assert _status_of(db_path, "r2") == "applied"


class TestUnknownPath:
    def test_approved_with_no_bean_skipped_and_stays_new(self, env):
        db_path, data_dir = env
        _create_frontend_db(
            db_path,
            [("r3", "/TestRoaster/no_such_bean", '[{"key": "decision", "value": "approved"}]', "new")],
        )

        apply_review_decisions(from_db=db_path, data_dir=data_dir, dry_run=False, verbose=False)

        assert _review_files(data_dir) == []
        assert _status_of(db_path, "r3") == "new"


class TestIdempotency:
    def test_rerun_writes_nothing_new(self, env):
        db_path, data_dir = env
        _create_frontend_db(
            db_path,
            [("r1", BEAN_ENTITY_PATH, '[{"key": "decision", "value": "approved"}]', "new")],
        )

        apply_review_decisions(from_db=db_path, data_dir=data_dir, dry_run=False, verbose=False)
        before = len(_review_files(data_dir))
        assert before == 1

        # Second run: the row is now 'applied' so it is not reprocessed.
        apply_review_decisions(from_db=db_path, data_dir=data_dir, dry_run=False, verbose=False)
        assert len(_review_files(data_dir)) == before
        assert _status_of(db_path, "r1") == "applied"
