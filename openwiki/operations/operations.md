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

### Database
| Command | Description |
|---|---|
| `serve` | Start the API server (add `--reload` for dev) |
| `dev` | Start API with auto-reload (add `--frontend` to also start frontend) |
| `refresh` | Load scraped JSON into DuckDB (`--incremental` for diff-based loading) |
| `refresh-media` | Rebuild the `podcasts.duckdb` database from podcast analysis JSON (independent of the main coffee bean refresh) |
| `validate-db` | Validate DuckDB integrity (volume drift, nulls, referential integrity, normalization, freshness, FTS divergence, in-stock drift, batch health) |
| `deduplicate-regions` | Region name deduplication |
| `validate-mappings` | CI check: fail on duplicate varietal/processing-method mappings |
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

### Categorization (`kissaten categorize ...`)
A Typer sub-app (`categorize_app`, registered as `app.add_typer(categorize_app, name="categorize")`) wraps the AI categorizers:
| Command | Description |
|---|---|
| `categorize processing` | Standardize processing-method names via `ProcessCategorizer` (`--review-and-merge` to run the merge phase) |
| `categorize varietals` | Standardize varietal names via `VarietalCategorizer` |
| `categorize tasting-notes` | Categorize tasting notes via `TastingNoteCategorizer` |
| `categorize all` | Run all three categorizers |

### Cache (`src/kissaten/cache/`)
| Command | Description |
|---|---|
| `cache-stats` | AI search / media insights cache statistics |
| `cache-cleanup` | Remove expired cache entries |
| `cache-clear` | Clear the cache |

### Inspection
| Command | Description |
|---|---|
| `list-scrapers` | List all registered scrapers with status |
| `test-scraper <scraper>` | Test a scraper without saving data |
| `scraper-info <scraper>` | Show info about a scraper |
| `show-bean` | Show a bean's stored data |
| `list-sessions` | List scraping sessions |

## Scheduled Scraping

See `docs/SCHEDULING.md` for full details.

### Default Schedule
16 hourly batches, 04:00–19:00 UTC. Scraping runs every tick; refresh and validate run **every 3rd tick** (batch indices 3, 6, 9, 12, 15 → hours 07, 10, 13, 16, 19 UTC), so data is at most ~3 hours stale. Each cron tick:
1. Filter scrapers by `--status available`
2. Shuffle with `random.Random(f"kissaten-{date}")` — deterministic per day, fresh each day
3. Pick the chunk for the batch index
4. Run scrapers sequentially (`--max-concurrent 1`)
5. Log per-scraper and run-level stats to Logfire
6. On refresh ticks only: run `kissaten refresh --incremental` as subprocess
7. On refresh ticks only: run `kissaten validate-db` as subprocess

Each tick's full trace shows as one timeline in Logfire.

### Cron Example (Compact)
```cron
# Scrape-only hours (4–6, 8–9, 11–12, 14–15, 17–18)
0 4-6,8-9,11-12,14-15,17-18 * * * cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index $((10#$(date +\%H) - 4)) --no-refresh --no-validate >> /var/log/kissaten/scrape.log 2>&1
# Refresh+validate hours (07, 10, 13, 16, 19)
0 7-19/3 * * * cd /srv/kissaten && /usr/local/bin/uv run kissaten run-all-scrapers --num-batches 16 --batch-index $((10#$(date +\%H) - 4)) >> /var/log/kissaten/scrape.log 2>&1
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
    └── test_db_processing_mapping_case_insensitive.py
```

## Database Validation (`kissaten validate-db`)

Eight check categories against `data/rw_kissaten.duckdb`:
1. **Volume drift** — Bean count vs last-known-good snapshot
2. **Required-field nulls** — Critical fields must not be null
3. **Referential integrity** — Foreign key consistency (origins ↔ beans ↔ roasters)
4. **Normalization invariants** — Price → price_usd conversion, currency_rates consistency
5. **24h freshness** — Data must be no more than 24 hours stale
6. **FTS index divergence** — FTS index must match base table row counts (split across three sub-checks: index existence, FTS source tables, and a match probe)
7. **In-stock drift** — In-stock bean count drift vs snapshot
8. **Batch health** — Per-scraper success/failure from the batch results JSON (`--batch-results`)

Exits 1 on any failure, preventing promotion of rw DB to production.

## Scraping env-var gotcha

`src/kissaten/cli/main.py:31` calls `dotenv.load_dotenv()` with `override=False`. If a parent shell exports any `.env` key to an empty string — e.g. `export LOGFIRE_TOKEN="${LOGFIRE_TOKEN:-}"` in a wrapper script — the CLI fails at import time with `LogfireConfigError: Hey, looks like you don't have Pydantic Logfire configured yet`, even though `.env` has the token. The error message points at `.env`, but `.env` is fine; the empty shell value is shadowing it.

**Rule for any wrapper script that spawns `kissaten`**: `unset` the `.env` keys first, rather than exporting a default:

```bash
unset LOGFIRE_TOKEN GOOGLE_API_KEY
uv run kissaten scrape <slug>
```

Never write `export VAR="${VAR:-}"` — the empty default is exported and wins over `.env`. The same trap applies to `OPENEXCHANGERATES_APP_ID`, `OPENCAGE_API_KEY`, `HF_TOKEN`, `JINA_API_KEY`, and any other key in `.env`. The fix is identical for all of them.

## Proxy Configuration

See `docs/PROXY_CONFIGURATION.md`. Set in `.env`:
```bash
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=https://proxy.example.com:8443
```
Both the curl_cffi-backed scraper shim (`src/kissaten/scrapers/_curl_http.py`) and Playwright (JS-heavy sites) use configured proxies. HTTPS_PROXY is preferred when both are set. Bare `httpx` is still used by the API/services layer (`api/podcast_db.py`, `api/fx.py`, `services/geocoding.py`) — only the scrapers were swapped to curl_cffi, see [curl_cffi Swap — 2026-08](curl-cffi-swap-2026-08.md).

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
| `ingest_podcasts.py` | Ingest podcast data |
| `capture_flavour_images.py` | Capture flavour images for UI |
| `migrate_schema.py` | DuckDB schema migration (repo root, not `scripts/`) |
| `migrate_elevation.py` | Elevation data migration (repo root, not `scripts/`) |


## Data Hygiene: Tasting Notes Non-Flavour Audit

An audit of `tasting_notes_categorized.csv` and the bean JSON `tasting_notes` arrays found 76 non-flavour metadata tokens (numbers, times, places, varieties, processes, field labels) mis-tagged as flavour notes, affecting 50 bean files. See [Tasting Notes Non-Flavour Audit — 2026-08](tasting-notes-non-flavour-audit-2026-08.md) for the flagged-token list, DB findings, the dry-run strip plan, and recommended CSV follow-ups.

### Orphaned diffjson Cleanup — 2026-08

`logs/refresh.log` accumulates *"no matching bean found for URL"* skips whenever a `.diffjson` update references a product with no backing `*.json` bean (non-bean products, delisted items, or products that never produced a base json). 413 such orphaned `.diffjson` files across `data/roasters` were removed. See [Orphaned diffjson Cleanup — 2026-08](diffjson-orphan-cleanup-2026-08.md) for the selection criteria (scoped to paths the refresh log reported, not a broad filesystem sweep) and follow-up suggestions.
ned diffjson Cleanup — 2026-08](diffjson-orphan-cleanup-2026-08.md) for the selection criteria (scoped to paths the refresh log reported, not a broad filesystem sweep) and follow-up suggestions.
`.diffjson` files across `data/roasters` were removed. See [Orphaned diffjson Cleanup — 2026-08](diffjson-orphan-cleanup-2026-08.md) for the selection criteria (scoped to paths the refresh log reported, not a broad filesystem sweep) and follow-up suggestions.
