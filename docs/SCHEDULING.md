# Scheduled Scraping

`kissaten run-all-scrapers` can be split across the day so we don't firehose
~150+ roasters in a single tick. A 16-batch hourly schedule is the supported
default, but the mechanism is generic: any number of batches is fine.

## How it works

Three flags on `run-all-scrapers` control the schedule:

| Flag | Purpose |
|---|---|
| `--num-batches N` | Split the shuffled scraper list into N roughly-equal chunks. Default `1` (run everything). |
| `--batch-index I` | 0-indexed chunk to run. Must satisfy `0 <= I < N`. Default `0`. |
| `--date YYYY-MM-DD` | Seed source for the shuffle. Defaults to today (UTC). Use to replay/backfill. |

The shuffle is seeded with `kissaten-<date>`, so:

- All 16 cron ticks on a given day see the **same** order — batch 0's last
  scraper is batch 1's first scraper, etc.
- The next day gets a **fresh** order, so we don't establish a fixed
  fingerprint per roaster over time.
- Replaying a past day with `--date 2026-07-02` is fully deterministic.

Chunks are interleaved (`[s0, sN, s2N, ...]`) rather than contiguous slices,
so each batch contains a mix of "early" and "late" scrapers in the shuffle
instead of always being the same prefix.

The default `--status available` filter is preserved, so the chunking happens
after filtering.

## Recommended cron (16 hourly batches, 04:00–20:00 UTC)

One line per slot is the readable form. The `$((10#$(date +\%H) - 4))`
arithmetic in the compact form computes `batch-index` from the current hour.

### Readable form

```cron
# 16 hourly scraper batches, 04:00–19:00 UTC, 1 batch per slot
0 4  * * *  cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index 0   >> /var/log/kissaten/scrape.log 2>&1
0 5  * * *  cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index 1   >> /var/log/kissaten/scrape.log 2>&1
0 6  * * *  cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index 2   >> /var/log/kissaten/scrape.log 2>&1
0 7  * * *  cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index 3   >> /var/log/kissaten/scrape.log 2>&1
0 8  * * *  cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index 4   >> /var/log/kissaten/scrape.log 2>&1
0 9  * * *  cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index 5   >> /var/log/kissaten/scrape.log 2>&1
0 10 * * *  cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index 6   >> /var/log/kissaten/scrape.log 2>&1
0 11 * * *  cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index 7   >> /var/log/kissaten/scrape.log 2>&1
0 12 * * *  cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index 8   >> /var/log/kissaten/scrape.log 2>&1
0 13 * * *  cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index 9   >> /var/log/kissaten/scrape.log 2>&1
0 14 * * *  cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index 10  >> /var/log/kissaten/scrape.log 2>&1
0 15 * * *  cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index 11  >> /var/log/kissaten/scrape.log 2>&1
0 16 * * *  cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index 12  >> /var/log/kissaten/scrape.log 2>&1
0 17 * * *  cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index 13  >> /var/log/kissaten/scrape.log 2>&1
0 18 * * *  cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index 14  >> /var/log/kissaten/scrape.log 2>&1
0 19 * * *  cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index 15  >> /var/log/kissaten/scrape.log 2>&1
```

### Compact form

```cron
0 4-19 * * * cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index $((10#$(date +\%H) - 4)) >> /var/log/kissaten/scrape.log 2>&1
```

Both forms behave identically. The per-line form is easier to comment/disable
individual slots; the compact form is shorter and harder to typo.

## What each tick does

1. Filter scrapers by `--status` (default `available`).
2. Shuffle with `random.Random(f"kissaten-{date}")` so order is deterministic
   for that day.
3. Pick the chunk for `--batch-index`.
4. Run those scrapers sequentially (`--max-concurrent 1` by default).
5. On success/failure, log per-scraper and run-level stats to logfire.
6. Run `kissaten refresh --incremental` as a subprocess so the DB picks up
   everything this batch wrote. Pass `--no-refresh` to skip the refresh
   (e.g. when you'd rather a single nightly refresh in a separate cron).
7. Run `kissaten validate-db` as a subprocess to catch silent data loss,
   referential-integrity damage, normalization regressions, and stale
   refreshes. Pass `--no-validate` to skip this step.

Each of those four phases is its own logfire span under a single parent
`run_all_scrapers_batch` span, so a tick's full trace (scrape → refresh →
validate) shows up as one timeline in the logfire UI. Every per-scraper
log event carries `batch_index`, `num_batches`, `date`, `seed`, and
`duration_seconds` so you can filter by batch or chart scrape duration
without correlating across unrelated events.

## Database refresh

By default, each batch runs `kissaten refresh --incremental` afterwards.
Smaller, more frequent refreshes are faster than one big nightly rebuild
and mean search results are usually no more than ~1 hour stale.

## Database validation

After a successful refresh, the same tick runs `kissaten validate-db`
against `data/rw_kissaten.duckdb`. The check set is:

- **A. Volume drift** — table row counts vs. last-known-good snapshot (±2 %)
- **B. Required fields** — `name`, `roaster`, `url`, `scraped_at`, `in_stock` non-null
- **C. Referential integrity** — beans↔roasters and beans↔origins links intact
- **D. Normalization** — `price`→`price_usd` and `currency_rates` coverage
- **E. Freshness** — at least one bean scraped in the last 24 h
- **F. FTS index** — `coffee_beans_fts_source` within 200 rows of `coffee_beans`

A failure does **not** fail the cron tick (the rw DB itself is still
valid; we just shouldn't promote it to production). It logs an error
event and prints a red `❌` to the cron log. Pass `--no-validate` to
skip the check entirely (e.g. on the first run of a day, when you're
seeding a fresh DB and don't have a baseline snapshot yet).

The baseline snapshot lives at `data/.last_good_counts.json`. After a
green validation pass, you can refresh it with:

```bash
kissaten validate-db --update-snapshot
```

Only do this once the current DB is known-good; the snapshot is the
reference for tomorrow's drift check, so re-baselining against a bad
DB hides future regressions.

If you'd rather have a single nightly refresh:

```cron
0 4-18 * * * cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 15 --batch-index $((10#$(date +\%H) - 4)) --no-refresh >> /var/log/kissaten/scrape.log 2>&1
0 19 * * *   cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 15 --batch-index 14                                          >> /var/log/kissaten/scrape.log 2>&1
0 20 * * *   cd /srv/kissaten && /usr/local/bin/uv run kissaten refresh --incremental                                                                  >> /var/log/kissaten/refresh.log 2>&1
```

## Manual replay / backfill

To re-run a specific batch for a past day (useful for retrying a slot that
crashed):

```bash
kissaten run-all-scrapers --num-batches 16 --batch-index 3 --date 2026-07-02
```

Two runs of the same `(date, batch-index)` pair produce the same scraper
set, so you can correlate logs to the exact set of roasters that tick
should have touched.

To see what a batch would run without actually running it, add
`--max-concurrent 0` — wait, that's a no-op. Use `--continue-on-error` plus
a single dry-run, or just read the log line "Scrapers in this batch: ..."
that the CLI prints at startup.

## Tradeoffs and known limitations

- **No overlap protection.** A hung Playwright run that exceeds the hourly
  window will collide with the next cron tick. Acceptable for now; add
  `flock` (e.g. `flock -n /var/lock/kissaten.scheduler.lock …`) in the cron
  command if a slow scraper becomes a real problem.
- **No leader election.** If the cron host changes timezone (e.g. DST) you
  can get duplicate or skipped batches at the transition. Use UTC throughout.
- **Random order is per-day, not per-batch.** That is the whole point: each
  batch doesn't re-shuffle, so the cumulative schedule stays randomised but
  reproducible.
- **The refresh subprocess uses the production DB.** That's intentional
  (the CLI sets `KISSATEN_ALLOW_PRODUCTION_DB=1` via `kissaten refresh`),
  but means tests must not invoke this CLI against the real DB.
