---
type: "Reference"
title: "Operations"
description: "CLI commands, scheduled scraping, testing, database validation, proxy config, deployment, CI/CD, and maintenance scripts for Kissaten."
---

# Operations

## CLI Commands

The CLI is built with Typer + Rich and lives in `src/kissaten/cli/main.py`. Invoke via `uv run python -m kissaten.cli.main <command>` or `kissaten <command>` (if installed).

### Scraping
| Command | Description |
|---|---|
| `scrape <scraper>` | Scrape a single roaster |
| `run-all-scrapers` | Scrape all available roasters (supports batch mode) |
| `list-scrapers` | List all registered scrapers with status |
| `test-scraper <scraper>` | Test a scraper without saving data |

### Database
| Command | Description |
|---|---|
| `serve` | Start the API server (add `--reload` for dev) |
| `dev` | Start API with auto-reload (add `--frontend` to also start frontend) |
| `refresh` | Load scraped JSON into DuckDB (`--incremental` for diff-based loading) |
| `validate-db` | Validate DuckDB integrity (volume drift, nulls, referential integrity, normalization, freshness, FTS index, in-stock drift, batch health) |
| `stats` | Show database statistics |

### Batch Scraping Flags
```
kissaten run-all-scrapers --num-batches 16 --batch-index 0 --date 2024-01-15
```
- `--num-batches N` — Split scrapers into N chunks
- `--batch-index I` — Run chunk I (0-indexed)
- `--date YYYY-MM-DD` — Seed for deterministic shuffle (defaults to today UTC)
- `--no-refresh` — Skip auto `refresh --incremental` after batch
- `--no-validate` — Skip auto `validate-db` after batch

## Scheduled Scraping

See `docs/SCHEDULING.md` for full details.

### Default Schedule
16 hourly batches, 04:00–19:00 UTC. Each cron tick:
1. Filter scrapers by `--status available`
2. Shuffle with `random.Random(f"kissaten-{date}")` — deterministic per day, fresh each day
3. Pick the chunk for the batch index
4. Run scrapers sequentially (`--max-concurrent 1`)
5. Log per-scraper and run-level stats to Logfire
6. Run `kissaten refresh --incremental` as subprocess
7. Run `kissaten validate-db` as subprocess

Each tick's full trace (scrape → refresh → validate) shows as one timeline in Logfire. The refresh and validate subprocesses are built with `_subprocess_for_cli` (`src/kissaten/cli/main.py`), which prefers the `kissaten` console script on PATH and falls back to `python -c "from kissaten.cli import app; app()"` so it works in cron and containers where PATH may be empty (`python -m kissaten.cli` is not usable because `kissaten.cli` is a package without `__main__`).

### Cron Example (Compact)
```cron
0 4-19 * * * cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index $((10#$(date +\%H) - 4)) >> /var/log/kissaten/scrape.log 2>&1
```

## Testing

See `docs/TESTING.md` for full reference.

### Test Database Isolation
- `tests/conftest.py` redirects `kissaten.api.db.conn` to a per-session temp DuckDB file via `KISSATEN_DATABASE_PATH` and `KISSATEN_USE_RW_DB=1`
- Safety guard in `src/kissaten/api/db.py` refuses to open production DBs without `KISSATEN_ALLOW_PRODUCTION_DB=1`
- The `kissaten refresh` CLI auto-sets the override

### Running Tests
```bash
uv run pytest -v                           # All tests
uv run pytest --cov=src/kissaten            # With coverage
uv run pytest tests/test_search_coffee_beans.py -v  # Specific file
uv run pytest -k "test_scraper" -v          # Pattern match
```

### Test Structure
```
tests/
├── conftest.py                      # Fixtures, DB isolation, test setup
├── test_search_coffee_beans.py      # Search functionality
├── test_security_hardening.py       # DuckDB security guard
├── test_safety_guard.py             # Production DB safety
├── test_beanconqueror_share.py      # BeanConqueror protobuf share
├── test_api_brew_assistant.py       # Brew assistant API
├── test_api_roasters.py             # Roasters API
├── test_incremental_updates.py      # Incremental DB loading
├── test_fts_feature.py              # Full-text search
├── test_stock_functionality.py      # Stock tracking
├── test_region_*.py                 # Region mapping consistency
├── test_varietal_mappings.py         # Varietal mapping validation
├── test_slugify_sync.py             # Slugify function consistency
├── test_origin_*.py                 # Origin hierarchy & search
├── test_tasting_note_*.py           # Tasting note categorization
├── test_proxy_configuration.py      # Proxy settings
└── unit/
    ├── test_shopify_scraper.py      # Shopify scraper unit tests
    ├── test_validation_gate.py     # AI validation gate
    ├── test_processing_method_mappings_validator.py
    ├── test_varietal_mappings_validator.py
    ├── test_db_processing_mapping_case_insensitive.py
    ├── test_validate_db_checks.py # validate-db G (in-stock drift) and H (batch health) checks
    └── test_out_of_stock_guard.py # out-of-stock update suppression on failed listing fetches
```

## Database Validation (`kissaten validate-db`)

Eight check categories (A–H) against `data/rw_kissaten.duckdb`, each wrapped in its own Logfire span:
1. **A. Volume drift** — Bean/origin/roaster counts vs last-known-good snapshot (`data/.last_good_counts.json`), ±2 % tolerance
2. **B. Required-field nulls** — `name`, `roaster`, `url`, `scraped_at`, `in_stock` must not be null
3. **C. Referential integrity** — beans↔roasters and beans↔origins links intact
4. **D. Normalization invariants** — price→price_usd conversion, currency_rates coverage
5. **E. Freshness** — At least one bean scraped within the last 24 h
6. **F. FTS index** — Three sub-checks that catch the failure modes where `/search?fts_query=...` silently returns zero results:
   - **F1 source divergence** — `coffee_beans_fts_source` row count within 200 of `coffee_beans`
   - **F2 index artifacts** — `fts_main_coffee_beans_fts_source.docs`/`.terms` tables exist and keep pace with the source table
   - **F3 match probe** — `match_bm25` returns ≥1 hit for a probe term derived from a live bean name (mirrors the exact `/search` call shape)
7. **G. In-stock drift** — Global in-stock count within 30 % of the snapshot, and no roaster with ≥10 previously in-stock beans has been wiped to zero (catches a mass `in_stock` true→false flip that volume drift cannot see)
8. **H. Batch health** — The last scraping batch (`data/last_batch_results.json`, written by `run-all-scrapers`) did not mostly fail: failed scrapers must be <50 % of the batch and total beans found must be >0. Results older than 36 h are ignored so validation does not deadlock when scraping is paused.

Exits 1 on any failure, preventing promotion of rw DB to production. Pass `--update-snapshot` to re-baseline the A/G counts after a legitimate catalogue change.

## Proxy Configuration

See `docs/PROXY_CONFIGURATION.md`. Set in `.env`:
```bash
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=https://proxy.example.com:8443
```
Both httpx (HTTP requests) and Playwright (JS-heavy sites) use configured proxies. HTTPS_PROXY is preferred when both are set.

## Deployment

### Backend
- Production: `uv run python -m kissaten.cli.main serve --workers 4`
- systemd service behind nginx reverse proxy
- DuckDB files: `data/kissaten.duckdb` (read-only, served) and `data/rw_kissaten.duckdb` (read-write, refreshed by cron)
- **Low-memory VPS**: The read-write DuckDB connection sets `preserve_insertion_order = false` to reduce memory pressure during `refresh` on low-memory systems. The `load_coffee_data` function also uses an explicit `columns=` schema when reading JSON files, ensuring all fields are projected even when some JSON files are missing optional fields.

### Frontend
- `cd frontend && bun run build` for production build
- Served via SvelteKit adapter

### Nginx
- Config in `nginx.kissaten.conf`
- Reverse proxies API (`/api/`) to FastAPI and serves static frontend

### Monitoring
- **Sentry**: Error tracking (frontend + backend, `SENTRY_DSN`)
- **Logfire**: Trace-level scraper observability with structured spans

## CI/CD

Two GitHub Actions workflows exist under `.github/workflows/`:
- `tests.yml` — Runs pytest with coverage on push/PR to `main`.
- `openwiki-update.yml` — Scheduled daily at 08:00 UTC (also `workflow_dispatch`); runs `openwiki code --update --print` and opens a PR with documentation changes.

## Maintenance Scripts (`scripts/`)

| Script | Purpose |
|---|---|
| `analyze_scraping_issues.py` | Diagnose scraping failures |
| `count_beans_from_json.py` | Count beans across all roaster data |
| `deduplicate_farms.py` | Farm name deduplication |
| `deduplicate_regions.py` | Region name deduplication |
| `fix_roaster_names.py` | Fix roaster name mismatches |
| `fix_tasting_notes.py` | Fix tasting note data |
| `get_blog_posts.py` | Scrape blog posts |
| `get_podcast_episodes.py` | Scrape podcast episodes |
| `get_wikidata_ids.py` | Fetch Wikidata IDs for entities |
| `scrape_coffee_varietals.py` | Scrape varietal reference data |
| `migrate_schema.py` | DuckDB schema migration |
| `migrate_elevation.py` | Elevation data migration |
| `ingest_podcasts.py` | Ingest podcast data |
| `capture_flavour_images.py` | Capture flavour images for UI |
