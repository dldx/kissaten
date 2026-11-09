---
type: "Operations"
title: "Incremental Refresh Memory & Performance Optimization — 2026-11"
description: "Investigation and fix for silent OOM crashes (>12.8 GB RSS) and multi-hour hangs in `kissaten refresh --incremental` caused by reading 1.58M diffjson files into DuckDB, unbatched commits, and unindexed lookups."
---

# Incremental Refresh Memory & Performance Optimization — 2026-11

## Context

Running `uv run kissaten refresh --incremental` was dying silently with no Python traceback immediately after printing:

```text
📁 Processing 3097 new/changed JSON files (skipping 19066 already processed)
```

Inspection of `dmesg` / `journalctl -k` revealed that the process was not throwing an unhandled Python exception, but was receiving `SIGKILL` from the Linux kernel OOM killer:

```text
kernel: Out of memory: Killed process 2381307 (kissaten) total-vm:35GB, anon-rss:12.8GB
```

Because `SIGKILL` cannot be caught or intercepted, the top-level exception handler in `src/kissaten/cli/main.py` never fired and exit code was `137`.

## Root Cause Analysis

Using `psutil` memory sampling and `/usr/bin/time -v` on an isolated test copy of `rw_kissaten.duckdb`, four compounding bottlenecks were identified:

1. **Diffjson scrape date extraction (OOM trigger)**:
   - Line 2107 in `src/kissaten/api/db.py` originally created a temporary view `diffjson_scrape_dates`:
     ```sql
     CREATE TEMPORARY VIEW diffjson_scrape_dates AS
     SELECT DISTINCT split_part(filename, '/', -3), split_part(filename, '/', -2)
     FROM read_json('data/roasters/**/*.diffjson', filename=true, auto_detect=true, union_by_name=true, ignore_errors=true)
     ```
   - With ~1.58 million `.diffjson` files on disk, DuckDB attempted to scan, parse contents, auto-detect schemas, and union every file simultaneously in memory.
   - Resident memory ballooned past 12.8 GB within seconds, triggering the OOM killer.
   - The scrape date is encoded in the file path (`.../<roaster>/<YYYYMMDD>/...`), meaning the file contents never needed to be read.

2. **Unprocessed file filtering overhead (`filter_unprocessed_files`)**:
   - Constructing 1.58M `Path` objects and calling `Path.relative_to` took ~34s and ~2 GB RAM.
   - The function then generated an SQL statement with 1.58M `?` placeholders (`WHERE file_path IN (?, ...)`).

3. **Per-file WAL commit thrashing**:
   - `mark_file_processed` issued `conn.commit()` after every single file. In DuckDB, each commit fsyncs the write-ahead log (~20–90 ms per transaction on a large DB).
   - With a backlog of ~100k diffjson updates, row-by-row commits required >2 hours of synchronous disk I/O.

4. **Permanent diffjson backlog from unhandled skips**:
   - Skipped diffjson files (e.g. delisted products or URL percent-encoding discrepancies like `%E2` vs `%e2`) were never recorded in `processed_files`.
   - Every subsequent incremental refresh re-read, re-parsed, and re-skipped all ~108,000 unhandled diffjson files.

## Solutions Implemented

1. **Lightweight diffjson date extraction**:
   - Replaced DuckDB `read_json` over all `.diffjson` files with `glob.iglob`, extracting `(roaster, date)` string tuples directly from paths.
   - Materialized the small set into a temporary table `diffjson_scrape_dates`.
   - **Memory impact**: Reduced peak memory from **>12.8 GB to <30 MB** on this step.

2. **DuckDB memory ceiling**:
   - Added `SET memory_limit = '8GB';` (configurable via `KISSATEN_DUCKDB_MEMORY_LIMIT`) to the rw connection in `src/kissaten/api/db.py` to prevent DuckDB from claiming ~80% of system RAM.

3. **String-based file filtering**:
   - Replaced `Path.relative_to` with prefix string slicing (~50× faster, minimal memory).
   - Replaced giant `WHERE file_path IN (...)` queries with a single `WHERE file_type = ?` scan diffed against a Python set.

4. **Batch update coalescing & batch tracking**:
   - Added `urllib.parse.unquote` to bean URL matching so percent-encoded variations match reliably.
   - Coalesced chronological updates per bean in memory before executing SQL, reducing ~98k individual updates to ~16k unique bean updates.
   - Added `mark_files_processed_batch()` using NumPy column replacement scans to insert thousands of processed file records in ~1–3s instead of hours.
   - Marked all examined diffjson files (including skips) as processed so they are not re-inspected on subsequent runs.
   - Replaced the per-row JSON file marking loop in `load_coffee_data` with `mark_files_processed_batch`.

## Profiling & Verification Results

Measured with `/usr/bin/time -v` on a full replica of the 530 MB DuckDB database with all 1.58M diffjson files:

| Metric | Before Optimization | After Optimization (Initial Backlog) | Subsequent Incremental Run |
|---|---|---|---|
| **Peak Resident Memory (RSS)** | **>12.8 GB** (OOM killed) | **1.49 GB** | **1.39 GB** |
| **Exit Status** | `137` (SIGKILL) | `0` (Success) | `0` (Success) |
| **Diffjson backlog processed** | Failed / hung | 108,162 files in ~2 min | 0 files (already tracked) |
| **Wall Clock Duration** | Infinite / Crash | 8m 21s (one-time backlog catchup) | **44.5 seconds** |

All tests in `tests/test_incremental_updates.py` and `tests/test_security_hardening.py` continue to pass.
