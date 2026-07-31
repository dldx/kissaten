---
type: "How-To"
title: "Scraper Rerun Recipe — 2026-07-31"
description: How to identify today's failed scrapers and rerun them one at a time after a code-side fix lands. Documents the canonical 3-step recipe and the failure-signature taxonomy.
---

# Scraper Rerun Recipe — 2026-07-31

Canonical recipe for "I just landed a fix that should make some scrapers work again — what now?". Covers enumerating today's failures, deciding which are worth retrying, and the actual run loop.

## TL;DR

```bash
# 1. Identify today's failed Shopify scrapers (custom union of two files)
grep -A0 "❌ Failed" logs/scrape.log logs/scrape_refresh.log | grep -oE "❌ Failed [^ ]+ -" | sort -u

# 2. Filter to the ones in the failure-signature bucket your fix targets
#    (e.g. "Skipped out-of-stock updates: listing" for the Shopify ladder fix)

# 3. Run them one at a time, then refresh + validate once at the end
./scripts/rerun_failed_shopify_scrapers.sh --only <slug>   # single-scraper sanity check
./scripts/rerun_failed_shopify_scrapers.sh                 # full batch
uv run kissaten refresh --incremental
uv run kissaten validate-db
uv run kissaten validate-db --update-snapshot              # only after validation passes
cp data/rw_kissaten.duckdb data/kissaten.duckdb
```

The `scripts/rerun_failed_shopify_scrapers.sh` script is the canonical runner and handles the env-var shadowing trap (see `operations.md` §"Scraping env-var gotcha").

## Step 1 — Identify today's failed scrapers

Two log files cover today, and you need both:

- `logs/scrape.log` — the main seed run. Search for `seed=kissaten-$(date +%Y-%m-%d)` lines, then take `❌ Failed` lines below the last one.
- `logs/scrape_refresh.log` — the refresh retry path. This re-runs each batch's failed scrapers across days as a recovery mechanism, so a scraper that succeeded in the main seed but failed on the retry is **still failed today** from the data-freshness perspective.

Failure rows after line 138336 in `logs/scrape.log` (the `seed=kissaten-2026-07-31` boundary) plus any new `❌ Failed` lines in `logs/scrape_refresh.log` since the last `seed=kissaten-$(date - 1)` line are the complete today-failed set.

A scraper that is "failed today" may have looked fine in the main seed run but failed on the refresh retry path; this is the case that a single-file grep misses. On 2026-07-31, 8 of the 38 failed Shopify scrapers were visible only in the refresh retry path.

## Step 2 — Categorize by failure signature

The `❌ Failed` row's trailing reason tells you which fix path applies:

| Signature | What it means | Likely fix |
|---|---|---|
| `Skipped out-of-stock updates: listing` | products.json 429/network failure, listing-fetch guard fired | Shopify ladder fix (`shopify_base.py` per-page httpx→Playwright escalation) |
| `Skipped out-of-stock updates: listing fetch` | as above, but the error happens during the initial collection-page fetch before products.json | same as above (the base-class HTP fetch path) |
| `Skipped out-of-stock updates` (no suffix) | listing-fetch failed but the structured reason was empty | check the per-scraper log for the underlying error |
| `HTTP 403` or `HTTP 404` | permanent site block (Cloudflare, geo-restriction, dead endpoint) | not ladder-fix targetable; needs a separate scraper rewrite or a new proxy |
| `Unexpected error: <python exception>` | scraper-specific bug (e.g. Cartwheel's `cartwheel_coffee.py`) | needs code-side fix; not a transient failure |
| `💥 Error <name>` (in `scrape_refresh.log`) | the scraper raised an unhandled exception in the retry path | check the log file for the traceback |

The first three rows are the ladder-fix target. They are the main reason the `scripts/rerun_failed_shopify_scrapers.sh` script exists — the rerun is a "did the new ladder work?" check, not an exploration.

## Step 3 — Run

For a single scraper (sanity check that the fix actually recovered something):

```bash
./scripts/rerun_failed_shopify_scrapers.sh --only watchhouse
```

Watchhouse was the first roaster to recover on 2026-07-31 after the new Shopify ladder landed. Its log shows the canonical happy path:

```
INFO:httpx:GET https://watchhouse.com/.../products.json?limit=250&page=1 "HTTP/1.1 429 Too Many Requests"
WARNING:Received 429 Too Many Requests from https://watchhouse.com/.../products.json via httpx. Upgrading to Playwright in 5.00s...
INFO:Fetching Shopify products via Playwright: https://watchhouse.com/.../products.json
✓ success — 1 coffee bean
```

For the full batch, drop `--only`:

```bash
./scripts/rerun_failed_shopify_scrapers.sh
```

The script runs all pending scrapers sequentially, with one log file per scraper under `logs/reruns/` and a summary at the end. It does **not** touch the database — that's intentionally a separate step so you can review the JSON the scrapers wrote before committing them to the rw DB.

After the rerun finishes:

```bash
uv run kissaten refresh --incremental      # load JSON into rw DB
uv run kissaten validate-db                # gate before promotion
uv run kissaten validate-db --update-snapshot  # only after validation passes
cp data/rw_kissaten.duckdb data/kissaten.duckdb
```

## What to drop from the rerun list

Drop or separately investigate any scraper whose failure signature is:

- `HTTP 403` / `HTTP 404` — permanent block, the ladder fix won't change the outcome (on 2026-07-31 this was `extract`, `los-amigos-coffee`, `revel-coffee`, `ukkei`).
- `Unexpected error: <crash>` — bug, not transient (only `cartwheel` on 2026-07-30).
- `💥 Error <name>` — crash in retry path, investigate the traceback before retrying.

These scrapers will keep failing in the rerun and waste a slot. The script does not currently filter them out — the failure-signature taxonomy above is the manual filter.

## Learnings baked into the script

- **Per-scraper `kissaten refresh --incremental` removed** — running refresh between scrapers floods the page-without-OOS-guards race window if the script is interrupted. Cleaner to refresh once at the end.
- **Env-var shadowing fix** — the script `unset`s `LOGFIRE_TOKEN` and `GOOGLE_API_KEY` before spawning `kissaten` because `dotenv.load_dotenv()` in `src/kissaten/cli/main.py:31` won't override shell-set values. See `operations.md` §"Scraping env-var gotcha" for the full rationale.
- **Sequential, not concurrent** — `kissaten scrape` is already heavier than `run-all-scrapers --max-concurrent 1` because each `scrape` spawns its own process. Keep it sequential and let the file logs be the source of truth.
