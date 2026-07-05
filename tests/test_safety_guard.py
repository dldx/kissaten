"""
Regression tests for the production-DB safety guard in ``kissaten.api.db``.

The guard exists to prevent the test suite (or any script) from accidentally
opening ``data/rw_kissaten.duckdb`` (the developer's working database) or
``data/kissaten.duckdb`` (the production read-only API database) with a
writable DuckDB config. The guard only fires when:

  1. The resolved path is one of the protected production DBs, AND
  2. The connection config is the writable form
     (i.e. ``enable_external_access`` is not ``False``), AND
  3. ``KISSATEN_ALLOW_PRODUCTION_DB`` is not set to ``"1"``.

Each scenario is exercised in a subprocess so we get a clean module-import
state — the conftest's pre-import env-var setup doesn't leak between cases.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
RW_DB = PROJECT_ROOT / "data" / "rw_kissaten.duckdb"
RO_DB = PROJECT_ROOT / "data" / "kissaten.duckdb"


def _run_import(env_overrides: dict[str, str], extra_args: list[str] | None = None) -> subprocess.CompletedProcess:
    """Run ``import kissaten.api.db`` in a clean subprocess and return the result.

    Sets the project's ``src/`` on ``PYTHONPATH`` so the import resolves.
    Pass ``extra_args`` to evaluate a one-liner after the import (e.g. to
    capture the resolved path).
    """
    env = os.environ.copy()
    env.pop("KISSATEN_DATABASE_PATH", None)
    env.pop("KISSATEN_USE_RW_DB", None)
    env.pop("KISSATEN_ALLOW_PRODUCTION_DB", None)
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    for key, value in env_overrides.items():
        env[key] = value

    code_lines = [
        "import kissaten.api.db as db",
        "print(db._get_database_path())",
    ]
    if extra_args:
        code_lines.extend(extra_args)

    return subprocess.run(
        [sys.executable, "-c", "\n".join(code_lines)],
        env=env,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


# ---------------------------------------------------------------------------
# Guard behaviour
# ---------------------------------------------------------------------------


def test_guard_refuses_protected_path_with_writable_config():
    """Setting KISSATEN_DATABASE_PATH to a protected DB with the rw config
    must raise ``RuntimeError`` when the guard is called directly.

    Note: the module-level ``_check_production_db_guard`` call in db.py is
    temporarily disabled (the API needs a permissive config to LOAD the FTS
    extension). This test calls the guard function directly so we still
    verify the guard logic itself remains correct for when it's re-enabled.
    """
    result = _run_import(
        {
            "KISSATEN_DATABASE_PATH": str(RW_DB),
            "KISSATEN_USE_RW_DB": "1",
        },
        extra_args=[
            "db._check_production_db_guard(db._get_database_path(), db._db_config)",
        ],
    )
    assert result.returncode != 0, (
        f"Expected non-zero exit. stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "RuntimeError" in result.stderr, (
        f"Expected RuntimeError. stderr={result.stderr!r}"
    )
    assert "Refusing to open protected database" in result.stderr
    assert "KISSATEN_ALLOW_PRODUCTION_DB" in result.stderr


def test_guard_refuses_kissaten_duckdb_with_writable_config():
    """The read-only production DB is also protected against writable configs
    when the guard is called directly."""
    result = _run_import(
        {
            "KISSATEN_DATABASE_PATH": str(RO_DB),
            "KISSATEN_USE_RW_DB": "1",
        },
        extra_args=[
            "db._check_production_db_guard(db._get_database_path(), db._db_config)",
        ],
    )
    assert result.returncode != 0
    assert "Refusing to open protected database" in result.stderr


def test_guard_allows_when_override_set():
    """Setting KISSATEN_ALLOW_PRODUCTION_DB=1 bypasses the guard for any path.

    Uses a temp file as the target so the test doesn't depend on the real
    rw_kissaten.duckdb being unlocked (the dev server often holds the lock).
    """
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="kissaten_test_override_"))
    target = tmp / "kissaten_test.duckdb"
    result = _run_import({
        "KISSATEN_DATABASE_PATH": str(target),
        "KISSATEN_USE_RW_DB": "1",
        "KISSATEN_ALLOW_PRODUCTION_DB": "1",
    })
    assert result.returncode == 0, (
        f"Expected success. stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert str(target) in result.stdout


def test_guard_allows_protected_path_with_restrictive_config():
    """``kissaten serve`` opens ``kissaten.duckdb`` with restrictive config
    (no env vars). The guard must not fire because the config is the
    read-only form.

    Tested by calling ``_check_production_db_guard`` directly so we don't need
    to actually open the (possibly locked) production database file.
    """
    # Fresh import under a temp dir so the module-level conn points at the
    # temp path and doesn't trigger the dev server's DuckDB lock.
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="kissaten_test_restrictive_"))
    old_env = os.environ.copy()
    try:
        os.environ["KISSATEN_DATABASE_PATH"] = str(tmp / "x.duckdb")
        os.environ.pop("KISSATEN_USE_RW_DB", None)
        if "kissaten.api.db" in sys.modules:
            del sys.modules["kissaten.api.db"]
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        import kissaten.api.db as db

        # The exact scenario kissaten serve would hit: restrictive config,
        # protected path, no override. Must not raise.
        db._check_production_db_guard(RO_DB, {"enable_external_access": False})

        # And the converse: same restrictive config on a non-protected path.
        db._check_production_db_guard(tmp / "x.duckdb", {"enable_external_access": False})
    finally:
        os.environ.clear()
        os.environ.update(old_env)
        for mod in list(sys.modules):
            if mod.startswith("kissaten"):
                del sys.modules[mod]


def test_guard_allows_temp_path_with_writable_config():
    """The conftest redirects to a temp DuckDB file with the rw config.
    The guard must not fire for paths outside ``data/``."""
    result = _run_import({
        "KISSATEN_DATABASE_PATH": "/tmp/kissaten_test_temp.duckdb",
        "KISSATEN_USE_RW_DB": "1",
    })
    assert result.returncode == 0, (
        f"Expected success. stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "/tmp/kissaten_test_temp.duckdb" in result.stdout


# ---------------------------------------------------------------------------
# Conftest integration
# ---------------------------------------------------------------------------


def test_conftest_model_resolves_to_temp_db():
    """The conftest's pre-import setup (KISSATEN_DATABASE_PATH=<tmp> + USE_RW_DB=1)
    must result in the module-level conn pointing at the temp file, not the
    real production DBs. We replicate the conftest's setup here (rather than
    re-running pytest) so the test stays self-contained and doesn't need
    pytest's full collection machinery.

    The conftest itself runs this same sequence at pytest startup; if the
    guard ever fires for a temp path, both this test and the whole test
    suite would break in the same way, which is the regression we want.
    """
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="kissaten_test_check_"))
    db_path = tmp / "kissaten_test.duckdb"

    old_env = os.environ.copy()
    try:
        os.environ["KISSATEN_DATABASE_PATH"] = str(db_path)
        os.environ["KISSATEN_USE_RW_DB"] = "1"
        if "kissaten.api.db" in sys.modules:
            del sys.modules["kissaten.api.db"]
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        import kissaten.api.db as db

        resolved = Path(db._get_database_path()).resolve()
        assert resolved.parent == tmp.resolve(), (
            f"Expected temp dir {tmp}, got {resolved.parent}"
        )
        assert resolved != RW_DB.resolve()
        assert resolved != RO_DB.resolve()
    finally:
        os.environ.clear()
        os.environ.update(old_env)
        for mod in list(sys.modules):
            if mod.startswith("kissaten"):
                del sys.modules[mod]


# ---------------------------------------------------------------------------
# Protected path resolution
# ---------------------------------------------------------------------------


def test_protected_path_resolution():
    """``_protected_db_paths()`` must return absolute paths to the two
    protected files under ``data/``.

    Imported in-process under a temp dir so the module-level conn doesn't
    try to open the (possibly locked) production database.
    """
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="kissaten_test_paths_"))
    old_env = os.environ.copy()
    try:
        os.environ["KISSATEN_DATABASE_PATH"] = str(tmp / "x.duckdb")
        if "kissaten.api.db" in sys.modules:
            del sys.modules["kissaten.api.db"]
        sys.path.insert(0, str(PROJECT_ROOT / "src"))
        import kissaten.api.db as db

        protected = {p.resolve() for p in db._protected_db_paths()}
        assert (PROJECT_ROOT / "data" / "rw_kissaten.duckdb").resolve() in protected
        assert (PROJECT_ROOT / "data" / "kissaten.duckdb").resolve() in protected
    finally:
        os.environ.clear()
        os.environ.update(old_env)
        for mod in list(sys.modules):
            if mod.startswith("kissaten"):
                del sys.modules[mod]


def test_rw_kissaten_duckdb_exists():
    """Sanity check — the working DB should exist on a real checkout so the
    guard's protection has something to guard."""
    if not RW_DB.exists():
        pytest.skip(f"rw_kissaten.duckdb not present at {RW_DB}")
    assert RW_DB.stat().st_size > 0
