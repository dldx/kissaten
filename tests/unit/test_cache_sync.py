"""Unit tests for the `kissaten cache-sync` CLI command.

The command mirrors the append-only raw-page cache to Cloudflare R2. These
tests never touch the network: they assert the rclone argv/env and exercise
the CLI with ``--dry-run`` and mocked ``subprocess.run``.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from kissaten.cli import main as cli_main


def _make_source(tmp_path: Path) -> Path:
    source = tmp_path / "roasters" / "example-roaster" / "20260101"
    source.mkdir(parents=True)
    (source / "example-bean.tar.gz").write_bytes(b"not-a-real-archive")
    return tmp_path / "roasters"


def test_build_copy_command_uses_copy_not_sync():
    cmd = cli_main._build_cache_copy_command(
        "/usr/bin/rclone",
        Path("data/cache/roasters"),
        "kissatenr2:kissaten/cache/roasters",
        16,
        32,
    )

    assert cmd[:4] == [
        "/usr/bin/rclone",
        "copy",
        "data/cache/roasters",
        "kissatenr2:kissaten/cache/roasters",
    ]
    assert "sync" not in cmd
    assert "--delete" not in cmd
    assert "--immutable" in cmd
    assert "--fast-list" in cmd
    assert cmd[cmd.index("--transfers") + 1] == "16"
    assert cmd[cmd.index("--checkers") + 1] == "32"
    assert cmd[cmd.index("--stats") + 1] == "30s"
    assert "--progress" in cmd
    assert "--dry-run" not in cmd


def test_build_copy_command_flags():
    cmd = cli_main._build_cache_copy_command(
        "rclone",
        Path("src"),
        "kissatenr2:bucket/prefix/roasters",
        4,
        8,
        dry_run=True,
        no_progress=True,
    )

    assert "--dry-run" in cmd
    assert "--progress" not in cmd
    assert "--delete" not in cmd


def test_verify_command_is_one_way_size_only():
    cmd = cli_main._build_cache_verify_command(
        "rclone", Path("data/cache/roasters"), "kissatenr2:kissaten/cache/roasters"
    )

    assert cmd[:2] == ["rclone", "check"]
    assert "--one-way" in cmd
    assert "--size-only" in cmd
    assert "--delete" not in cmd


def test_rclone_env_uses_undeclared_remote_and_keeps_secrets_out_of_argv(monkeypatch):
    env = cli_main._cache_sync_rclone_env(
        "https://account.r2.cloudflarestorage.com",
        "fake-access-key",
        "fake-secret-key",
        base_env={"PATH": "/usr/bin"},
    )

    assert env["RCLONE_CONFIG_KISSATENR2_TYPE"] == "s3"
    assert env["RCLONE_CONFIG_KISSATENR2_PROVIDER"] == "Cloudflare"
    assert env["RCLONE_CONFIG_KISSATENR2_ENDPOINT"] == "https://account.r2.cloudflarestorage.com"
    assert env["RCLONE_CONFIG_KISSATENR2_ACCESS_KEY_ID"] == "fake-access-key"
    assert env["RCLONE_CONFIG_KISSATENR2_SECRET_ACCESS_KEY"] == "fake-secret-key"
    assert env["RCLONE_CONFIG_KISSATENR2_REGION"] == "auto"
    assert env["PATH"] == "/usr/bin"


def test_cache_sync_dry_run_passes_argv_and_env_without_network(monkeypatch, tmp_path):
    source = _make_source(tmp_path)
    calls: list[dict] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append({"cmd": cmd, "env": kwargs.get("env")})
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli_main, "setup_logging", lambda verbose=False: None)
    monkeypatch.setattr(cli_main.shutil, "which", lambda name: "/usr/bin/rclone" if name == "rclone" else None)
    monkeypatch.setattr(cli_main.subprocess, "run", fake_run)

    result = CliRunner().invoke(
        cli_main.app,
        [
            "cache-sync",
            "--source-dir",
            str(source),
            "--bucket",
            "test-bucket",
            "--prefix",
            "cache",
            "--endpoint",
            "https://account.r2.cloudflarestorage.com",
            "--access-key-id",
            "fake-access-key",
            "--secret-access-key",
            "fake-secret-key",
            "--dry-run",
            "--no-progress",
        ],
    )

    assert result.exit_code == 0, result.output
    assert len(calls) == 1

    cmd = calls[0]["cmd"]
    env = calls[0]["env"]
    assert cmd[0] == "/usr/bin/rclone"
    assert cmd[1] == "copy"
    assert cmd[3] == "kissatenr2:test-bucket/cache/roasters"
    assert "--dry-run" in cmd
    assert "--progress" not in cmd
    assert "--delete" not in cmd
    assert "sync" not in cmd

    # Secrets live only in the environment, never in argv.
    joined = " ".join(cmd)
    assert "fake-access-key" not in joined
    assert "fake-secret-key" not in joined
    assert env["RCLONE_CONFIG_KISSATENR2_ACCESS_KEY_ID"] == "fake-access-key"
    assert env["RCLONE_CONFIG_KISSATENR2_SECRET_ACCESS_KEY"] == "fake-secret-key"


def test_cache_sync_verify_runs_check_after_copy(monkeypatch, tmp_path):
    source = _make_source(tmp_path)
    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli_main, "setup_logging", lambda verbose=False: None)
    monkeypatch.setattr(cli_main.shutil, "which", lambda name: "/usr/bin/rclone" if name == "rclone" else None)
    monkeypatch.setattr(cli_main.subprocess, "run", fake_run)

    result = CliRunner().invoke(
        cli_main.app,
        [
            "cache-sync",
            "--source-dir",
            str(source),
            "--bucket",
            "test-bucket",
            "--endpoint",
            "https://account.r2.cloudflarestorage.com",
            "--access-key-id",
            "fake-access-key",
            "--secret-access-key",
            "fake-secret-key",
            "--verify",
            "--no-progress",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls[0][1] == "copy"
    assert calls[1][:2] == ["/usr/bin/rclone", "check"]
    assert "--one-way" in calls[1]
    assert "--size-only" in calls[1]


def test_cache_sync_verify_failure_exits_non_zero(monkeypatch, tmp_path):
    source = _make_source(tmp_path)
    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0 if cmd[1] == "copy" else 3)

    monkeypatch.setattr(cli_main, "setup_logging", lambda verbose=False: None)
    monkeypatch.setattr(cli_main.shutil, "which", lambda name: "/usr/bin/rclone" if name == "rclone" else None)
    monkeypatch.setattr(cli_main.subprocess, "run", fake_run)

    result = CliRunner().invoke(
        cli_main.app,
        [
            "cache-sync",
            "--source-dir",
            str(source),
            "--bucket",
            "test-bucket",
            "--endpoint",
            "https://account.r2.cloudflarestorage.com",
            "--access-key-id",
            "fake-access-key",
            "--secret-access-key",
            "fake-secret-key",
            "--verify",
            "--no-progress",
        ],
    )

    assert result.exit_code == 1
    assert len(calls) == 2


def test_cache_sync_missing_source_exits_non_zero(monkeypatch, tmp_path):
    monkeypatch.setattr(cli_main, "setup_logging", lambda verbose=False: None)
    monkeypatch.setattr(cli_main.shutil, "which", lambda name: "/usr/bin/rclone" if name == "rclone" else None)

    result = CliRunner().invoke(
        cli_main.app,
        [
            "cache-sync",
            "--source-dir",
            str(tmp_path / "does-not-exist"),
            "--bucket",
            "test-bucket",
            "--endpoint",
            "https://account.r2.cloudflarestorage.com",
            "--access-key-id",
            "fake-access-key",
            "--secret-access-key",
            "fake-secret-key",
        ],
    )

    assert result.exit_code == 1
    assert "source directory not found" in result.output


def test_cache_sync_missing_rclone_exits_non_zero(monkeypatch, tmp_path):
    source = _make_source(tmp_path)
    monkeypatch.setattr(cli_main, "setup_logging", lambda verbose=False: None)
    monkeypatch.setattr(cli_main.shutil, "which", lambda name: None)

    result = CliRunner().invoke(
        cli_main.app,
        [
            "cache-sync",
            "--source-dir",
            str(source),
            "--bucket",
            "test-bucket",
            "--endpoint",
            "https://account.r2.cloudflarestorage.com",
            "--access-key-id",
            "fake-access-key",
            "--secret-access-key",
            "fake-secret-key",
        ],
    )

    assert result.exit_code == 1
    assert "rclone was not found" in result.output


def _make_roaster_source(tmp_path: Path, roaster: str) -> Path:
    source = tmp_path / "roasters" / roaster / "20260101"
    source.mkdir(parents=True)
    (source / "example-bean.tar.gz").write_bytes(b"not-a-real-archive")
    return tmp_path / "roasters"


def test_cache_sync_roaster_scopes_source_and_destination(monkeypatch, tmp_path):
    source = _make_roaster_source(tmp_path, "poma_coffee")
    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli_main, "setup_logging", lambda verbose=False: None)
    monkeypatch.setattr(cli_main.shutil, "which", lambda name: "/usr/bin/rclone" if name == "rclone" else None)
    monkeypatch.setattr(cli_main.subprocess, "run", fake_run)

    result = CliRunner().invoke(
        cli_main.app,
        [
            "cache-sync",
            "--source-dir",
            str(source),
            "--roaster",
            "poma_coffee",
            "--bucket",
            "test-bucket",
            "--prefix",
            "cache",
            "--endpoint",
            "https://account.r2.cloudflarestorage.com",
            "--access-key-id",
            "fake-access-key",
            "--secret-access-key",
            "fake-secret-key",
            "--no-progress",
        ],
    )

    assert result.exit_code == 0, result.output
    assert len(calls) == 1
    cmd = calls[0]
    assert cmd[1] == "copy"
    assert cmd[2] == str(source / "poma_coffee")
    assert cmd[3] == "kissatenr2:test-bucket/cache/roasters/poma_coffee"
    assert "--immutable" in cmd
    assert "sync" not in cmd
    assert "--delete" not in cmd
    # The printed summary shows the effective source and destination.
    assert "roasters/poma_coffee" in result.output


@pytest.mark.parametrize("invalid_roaster", ["../x", "a/b", ".", "..", ""])
def test_cache_sync_invalid_roaster_exits_non_zero(monkeypatch, tmp_path, invalid_roaster):
    source = _make_roaster_source(tmp_path, "poma_coffee")
    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli_main, "setup_logging", lambda verbose=False: None)
    monkeypatch.setattr(cli_main.shutil, "which", lambda name: "/usr/bin/rclone" if name == "rclone" else None)
    monkeypatch.setattr(cli_main.subprocess, "run", fake_run)

    result = CliRunner().invoke(
        cli_main.app,
        [
            "cache-sync",
            "--source-dir",
            str(source),
            "--roaster",
            invalid_roaster,
            "--bucket",
            "test-bucket",
            "--endpoint",
            "https://account.r2.cloudflarestorage.com",
            "--access-key-id",
            "fake-access-key",
            "--secret-access-key",
            "fake-secret-key",
        ],
    )

    assert result.exit_code == 1
    assert "invalid --roaster" in result.output
    assert calls == []


def test_cache_sync_missing_roaster_dir_exits_non_zero(monkeypatch, tmp_path):
    source = _make_roaster_source(tmp_path, "poma_coffee")
    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli_main, "setup_logging", lambda verbose=False: None)
    monkeypatch.setattr(cli_main.shutil, "which", lambda name: "/usr/bin/rclone" if name == "rclone" else None)
    monkeypatch.setattr(cli_main.subprocess, "run", fake_run)

    result = CliRunner().invoke(
        cli_main.app,
        [
            "cache-sync",
            "--source-dir",
            str(source),
            "--roaster",
            "does_not_exist",
            "--bucket",
            "test-bucket",
            "--endpoint",
            "https://account.r2.cloudflarestorage.com",
            "--access-key-id",
            "fake-access-key",
            "--secret-access-key",
            "fake-secret-key",
        ],
    )

    assert result.exit_code == 1
    assert "roaster cache directory not found" in result.output
    assert calls == []


def test_cache_sync_roaster_verify_uses_scoped_paths(monkeypatch, tmp_path):
    source = _make_roaster_source(tmp_path, "poma_coffee")
    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli_main, "setup_logging", lambda verbose=False: None)
    monkeypatch.setattr(cli_main.shutil, "which", lambda name: "/usr/bin/rclone" if name == "rclone" else None)
    monkeypatch.setattr(cli_main.subprocess, "run", fake_run)

    result = CliRunner().invoke(
        cli_main.app,
        [
            "cache-sync",
            "--source-dir",
            str(source),
            "--roaster",
            "poma_coffee",
            "--bucket",
            "test-bucket",
            "--prefix",
            "cache",
            "--endpoint",
            "https://account.r2.cloudflarestorage.com",
            "--access-key-id",
            "fake-access-key",
            "--secret-access-key",
            "fake-secret-key",
            "--verify",
            "--no-progress",
        ],
    )

    assert result.exit_code == 0, result.output
    assert len(calls) == 2
    scoped_source = str(source / "poma_coffee")
    scoped_destination = "kissatenr2:test-bucket/cache/roasters/poma_coffee"

    assert calls[0][1] == "copy"
    assert calls[0][2] == scoped_source
    assert calls[0][3] == scoped_destination

    assert calls[1][1] == "check"
    assert scoped_source in calls[1]
    assert scoped_destination in calls[1]
    assert "--one-way" in calls[1]
    assert "--size-only" in calls[1]

