#!/usr/bin/env python3
"""Identify and quarantine bogus out-of-stock diffjson files.

Background: when a scraper's listing fetch fails (network error, 403, proxy
outage), older code still wrote ``*_out_of_stock.diffjson`` files for every
historically known bean of that roaster, flipping the whole catalogue out of
stock in the database (see openwiki/operations/scraper-log-analysis-2026-07.md,
issue #2). The scraper-side guards now prevent new bogus files; this script
cleans up the historical ones.

Identification rule — a session directory's out-of-stock files are bogus iff:

1. The roaster's run that day FAILED according to logs/scrape.log
   (``❌ Failed`` / ``💥 Error`` lines; the 2026-07-27/28 proxy outage is
   covered automatically because every roaster failed those days), AND
2. The session dir has the "found nothing at all" signature: at least one
   ``*_out_of_stock.diffjson`` but zero in-stock diffjson and zero bean JSON
   files. This protects false-failure runs that were actually productive
   (e.g. The Naughty Dog's diffjson-only runs) and legit fully-sold-out days.

Usage:
    uv run python scripts/quarantine_bogus_oos.py --dry-run      # report only (default)
    uv run python scripts/quarantine_bogus_oos.py --quarantine   # move files out of data/

Quarantined files are moved to ``quarantine/2026-07-cleanup/`` (outside
``data/`` so the ``data/**/*.diffjson`` refresh glob can never replay them)
and a manifest.json is written there to drive the later DB-repair step.
"""

import argparse
import json
import re
import shutil
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

LOG_PATH = REPO_ROOT / "logs" / "scrape.log"
DATA_DIR = REPO_ROOT / "data"
ROASTERS_DIR = DATA_DIR / "roasters"
RW_DB_PATH = DATA_DIR / "rw_kissaten.duckdb"
QUARANTINE_DIR = REPO_ROOT / "quarantine" / "2026-07-cleanup"

SEED_RE = re.compile(r"seed=kissaten-(\d{4})-(\d{2})-(\d{2})")
SUCCESS_RE = re.compile(r"^✅ Success (.+?) - ")
FAILED_RE = re.compile(r"^❌ Failed (.+?) - ")
ERROR_RE = re.compile(r"^💥 Error (.+?) - ")
OOS_SUFFIX = "_out_of_stock.diffjson"


def build_roaster_dir_map() -> tuple[dict[str, str], dict[str, str]]:
    """Map display_name -> data dir name, using the scraper registry.

    Falls back to an accent-stripped normalized comparison against the
    directories that actually exist on disk (e.g. Kafferäven -> kafferaven,
    which the registry's slugifier does not produce).

    Returns:
        (display_name -> dir_name, dir_name -> roaster_name)
    """
    from kissaten.scrapers import get_registry

    existing_dirs = {p.name for p in ROASTERS_DIR.iterdir() if p.is_dir()}

    def normalize(s: str) -> str:
        s = unicodedata.normalize("NFKD", s.lower())
        s = "".join(c for c in s if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]", "", s)

    normalized_dirs = {normalize(d): d for d in existing_dirs}

    display_to_dir: dict[str, str] = {}
    dir_to_roaster: dict[str, str] = {}
    for info in get_registry().list_scrapers():
        dir_name = info.directory_name
        if dir_name not in existing_dirs:
            dir_name = normalized_dirs.get(normalize(info.roaster_name), info.directory_name)
        display_to_dir[info.display_name] = dir_name
        dir_to_roaster[dir_name] = info.roaster_name
    return display_to_dir, dir_to_roaster


def parse_failed_days(log_path: Path, display_to_dir: dict[str, str]) -> tuple[dict[str, set[str]], dict[str, int]]:
    """Parse scrape.log into {dir_name: set of yyyymmdd dates with failed runs}.

    A day is failed for a roaster if its run ended with ❌ Failed or 💥 Error.
    Successes on the same day take precedence (defensive; normally one
    run per roaster per day).
    """
    failed: dict[str, set[str]] = defaultdict(set)
    succeeded: dict[str, set[str]] = defaultdict(set)
    stats = {"unmapped_display_names": 0, "failed_lines": 0, "success_lines": 0}
    unmapped: set[str] = set()

    current_date: str | None = None
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            if m := SEED_RE.search(line):
                current_date = "".join(m.groups())
                continue
            if current_date is None:
                continue
            if m := SUCCESS_RE.match(line):
                outcome, name = succeeded, m.group(1)
                stats["success_lines"] += 1
            elif (m := FAILED_RE.match(line)) or (m := ERROR_RE.match(line)):
                outcome, name = failed, m.group(1)
                stats["failed_lines"] += 1
            else:
                continue
            dir_name = display_to_dir.get(name)
            if dir_name is None:
                if name not in unmapped:
                    unmapped.add(name)
                    stats["unmapped_display_names"] += 1
                continue
            outcome[dir_name].add(current_date)

    # A roaster-day with both outcomes counts as successful (conservative:
    # we only quarantine on unambiguous failure).
    for dir_name, dates in succeeded.items():
        failed[dir_name] -= dates

    if unmapped:
        print(f"WARNING: {len(unmapped)} display names not found in registry: {sorted(unmapped)}")
    return failed, stats


def session_dir_is_bogus(session_dir: Path) -> list[Path] | None:
    """Return the bogus out-of-stock files if the session dir has the
    'found nothing at all' signature, else None."""
    if not session_dir.is_dir():
        return None
    oos_files = list(session_dir.glob(f"*{OOS_SUFFIX}"))
    if not oos_files:
        return None
    if list(p for p in session_dir.glob("*.diffjson") if not p.name.endswith(OOS_SUFFIX)):
        return None  # in-stock updates exist -> run was productive
    if list(session_dir.glob("*.json")):
        return None  # new bean files exist -> run was productive
    return oos_files


def load_diffjson(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def compute_newest_flags(roaster_dir: Path, bogus_files: list[Path]) -> dict[Path, bool]:
    """For each bogus file, is it the newest stock observation for its URL?

    Observations for one bean share a filename stem across all session dirs
    of the roaster (<slug>_<hash8>[.diffjson|_out_of_stock.diffjson]).
    """
    by_stem: dict[str, list[Path]] = defaultdict(list)
    for session_dir in roaster_dir.iterdir():
        if session_dir.is_dir() and session_dir.name.isdigit():
            for f in session_dir.glob("*.diffjson"):
                stem = f.name.removesuffix(OOS_SUFFIX).removesuffix(".diffjson")
                by_stem[stem].append(f)

    flags: dict[Path, bool] = {}
    for bogus in bogus_files:
        stem = bogus.name.removesuffix(OOS_SUFFIX)
        bogus_data = load_diffjson(bogus) or {}
        bogus_ts = bogus_data.get("scraped_at") or ""
        newest = True
        for sibling in by_stem.get(stem, []):
            if sibling == bogus:
                continue
            sibling_ts = (load_diffjson(sibling) or {}).get("scraped_at") or ""
            if sibling_ts > bogus_ts:
                newest = False
                break
        flags[bogus] = newest
    return flags


def load_processed_paths() -> set[str] | None:
    """Load processed_files paths (relative to data/) from the rw DB, read-only."""
    if not RW_DB_PATH.exists():
        return None
    try:
        import duckdb

        con = duckdb.connect(str(RW_DB_PATH), read_only=True)
        try:
            rows = con.execute("SELECT file_path FROM processed_files WHERE file_type = 'diffjson'").fetchall()
        finally:
            con.close()
        return {row[0] for row in rows}
    except Exception as e:
        print(f"WARNING: could not read processed_files from {RW_DB_PATH}: {e}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Report only (default)")
    mode.add_argument("--quarantine", action="store_true", help="Move bogus files to the quarantine directory")
    args = parser.parse_args()

    if not LOG_PATH.exists():
        print(f"ERROR: log file not found: {LOG_PATH}")
        return 1

    display_to_dir, dir_to_roaster = build_roaster_dir_map()
    failed_days, log_stats = parse_failed_days(LOG_PATH, display_to_dir)
    print(
        f"Parsed log: {log_stats['success_lines']} success lines, {log_stats['failed_lines']} failure lines, "
        f"{len(failed_days)} roasters with failed days"
    )

    processed_paths = load_processed_paths()
    if processed_paths is None:
        print("NOTE: processed_files status unavailable; manifest will mark files as processed=unknown")

    manifest: list[dict] = []
    per_roaster_counts: dict[str, int] = defaultdict(int)
    skipped_productive: list[str] = []
    date_mismatches = 0

    for dir_name, dates in sorted(failed_days.items()):
        roaster_dir = ROASTERS_DIR / dir_name
        for date in sorted(dates):
            session_dir = roaster_dir / date
            oos_files = session_dir_is_bogus(session_dir)
            if oos_files is None:
                if session_dir.is_dir() and list(session_dir.glob(f"*{OOS_SUFFIX}")):
                    skipped_productive.append(f"{dir_name}/{date}")
                continue

            newest_flags = compute_newest_flags(roaster_dir, oos_files)
            for f in oos_files:
                data = load_diffjson(f) or {}
                scraped_at = data.get("scraped_at") or ""
                if scraped_at[:10].replace("-", "") != date:
                    date_mismatches += 1
                # processed_files stores paths relative to data/roasters/
                rel = f.relative_to(ROASTERS_DIR)
                manifest.append(
                    {
                        "src_path": str(rel),
                        "quarantine_path": str(QUARANTINE_DIR / rel),
                        "roaster_dir": dir_name,
                        "roaster_name": dir_to_roaster.get(dir_name, dir_name),
                        "session_date": date,
                        "url": data.get("url"),
                        "scraped_at": scraped_at,
                        "newest_for_url": newest_flags[f],
                        "processed": (str(rel) in processed_paths) if processed_paths is not None else None,
                    }
                )
                per_roaster_counts[dir_name] += 1

    total = len(manifest)
    newest_count = sum(1 for e in manifest if e["newest_for_url"])
    unprocessed_count = sum(1 for e in manifest if e["processed"] is False)

    print(f"\n=== Bogus out-of-stock diffjson files: {total} ===")
    print(f"  newest observation for their URL (DB currently wrong): {newest_count}")
    print(f"  not yet processed (would poison a future refresh):   {unprocessed_count}")
    print(f"  scraped_at/date mismatches (review manually):        {date_mismatches}")
    print(f"\nFailed-but-productive session dirs skipped (NOT bogus): {len(skipped_productive)}")
    for s in skipped_productive[:10]:
        print(f"  - {s}")
    if len(skipped_productive) > 10:
        print(f"  ... and {len(skipped_productive) - 10} more")

    print("\nTop roasters by bogus file count:")
    for dir_name, count in sorted(per_roaster_counts.items(), key=lambda kv: -kv[1])[:15]:
        print(f"  {count:6d}  {dir_name}")

    if args.quarantine:
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
        moved = 0
        for entry in manifest:
            src = ROASTERS_DIR / entry["src_path"]
            dst = Path(entry["quarantine_path"])
            if not src.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            moved += 1
        manifest_path = QUARANTINE_DIR / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
        print(f"\nQuarantined {moved}/{total} files to {QUARANTINE_DIR}")
        print(f"Manifest written to {manifest_path}")
    else:
        print(f"\nDry run — no files moved. Re-run with --quarantine to move them to {QUARANTINE_DIR}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
