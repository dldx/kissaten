# AGENTS.md - Kissaten Coffee Bean Scraper & Search App

This document provides project-specific guidance for AI coding assistants and developers. Source code and tests are authoritative; this file captures the non-obvious invariants and workflows.

## Project Overview

Kissaten is a coffee bean database and search application that scrapes coffee bean information from individual roasters worldwide. The project consists of:

- **Backend**: Python-based scrapers and API using modern Python tooling
- **Frontend**: SvelteKit-based web application for searching and browsing coffee beans
- **Database**: DuckDB for efficient data processing and analytics
- **Data**: Structured storage of coffee bean information in JSON format

## Architecture (key facts, not an exhaustive tree)

- `src/kissaten/scrapers/` holds one module per roaster (~400 scrapers), plus `base.py` (`BaseScraper`), `shopify_base.py`, `registry.py` (roaster registry), and per-platform patterns documented in the `shopify-scraper` / `squarespace-scraper` / `non-shopify-scraper` skills.
- `src/kissaten/api/` is the DB + API layer: `db.py` owns the DuckDB connection, `main.py` owns the FastAPI routes, `fx.py` currency handling, plus `ai_search.py`, `brew_assistant.py`, `podcasts.py`, `beanconqueror_share.py`.
- `src/kissaten/database/` holds static mappings/data assets (country codes, region mappings, varietal/processing/tasting-note mappings) — not a database class.
- `src/kissaten/schemas/` holds the Pydantic models (`coffee_bean.py`, `roaster.py`, `search.py`, `api_models.py`, `scraping_session.py`, `podcast.py`, `ai_search.py`, `geography_models.py`).
- `src/kissaten/services/` (geocoding), `src/kissaten/cli/` (Typer CLI), `src/kissaten/cache/`, `src/kissaten/ai/`, `src/kissaten/dedup/`.
- `frontend/` is a Svelte 5 (runes) app; routes live under `frontend/src/routes/(main)/` (search, origins, processes, varietals, tasting, flavours, brew-assistant, admin, vault, …) and `(no-layout)/`.
- `data/roasters/<roaster>/<YYYYMMDD>/` holds per-bean `<slug>_<HHMMSS>.json` files plus update artifacts (`<slug>_<hash8>.diffjson`, `_out_of_stock.diffjson`, `.review.diffjson`). DuckDB files (`kissaten.duckdb` prod, `rw_kissaten.duckdb` rw) live directly in `data/`.

## Technology Stack

### Backend

Python 3.10+, **uv** package manager, Pydantic v2, DuckDB, FastAPI, httpx, BeautifulSoup4/lxml, Playwright, Typer, rich, polars, logfire, pydantic-ai. Linting/formatting via **ruff** (line-length 120).

### Frontend

SvelteKit, Svelte 5 runes, TypeScript, Tailwind CSS v4, **Bun** package manager, shadcn-svelte/bits-ui, lucide-svelte.

## Database Modes (critical invariants)

> **Test database isolation** — the test suite never touches the developer's
> working databases. `tests/conftest.py` redirects `kissaten.api.db.conn` to
> a per-session temp DuckDB file via `KISSATEN_DATABASE_PATH` and
> `KISSATEN_USE_RW_DB=1`. A safety guard in `src/kissaten/api/db.py` refuses
> to open `data/rw_kissaten.duckdb` or `data/kissaten.duckdb` with a writable
> config unless `KISSATEN_ALLOW_PRODUCTION_DB=1` is set. The `kissaten
> refresh` CLI auto-sets the override. See `docs/TESTING.md` for the full
> reference.
>
> **Read-only API mode** — `kissaten serve` opens `data/kissaten.duckdb`
> with `read_only=True` (rw mode is selected by `KISSATEN_USE_RW_DB=1` and
> used by `kissaten refresh` and the tests). A read-only API process never
> creates a `.wal` file and cannot corrupt the DB when the file is swapped
> (`cp rw_kissaten.duckdb kissaten.duckdb`) while it runs. The `ensure_*`
> startup migrations only run in rw mode; the mutating FX endpoints return
> 409 in API mode. See `docs/TESTING.md`.

## Environment Variables

Real variables (see `src/kissaten/api/db.py` and `src/kissaten/cli/main.py`):

- **KISSATEN_DATABASE_PATH**: DuckDB file path (defaults to `data/kissaten.duckdb`)
- **KISSATEN_USE_RW_DB=1**: select the rw database (`data/rw_kissaten.duckdb`) — used by `kissaten refresh` and tests
- **KISSATEN_ALLOW_PRODUCTION_DB=1**: bypass the safety guard; required before opening the prod/rw DB writable from a test or one-off script
- **KISSATEN_INCREMENTAL=1**, **KISSATEN_CHECK_FOR_CHANGES=1**, **KISSATEN_REFRESH_MAPPINGS=1**: modes for the refresh pipeline
- **LOGFIRE_TOKEN**: logfire telemetry (loaded via `.env`)

## Scrapers

Each roaster has its own module in `src/kissaten/scrapers/`. All scrapers:

- Inherit from `BaseScraper` and implement async `scrape()` returning validated `CoffeeBean` objects
- Include error handling/retry, respect rate limiting, log with structured logging, and validate/clean data before returning
- Never hardcode bean values — extract from HTML/JSON and check extracted values are non-empty
- **Never write out-of-stock diffjson updates when the listing fetch failed**: `BaseScraper` tracks failed store/listing URLs per session and skips out-of-stock updates (an empty product list with non-empty history means the fetch failed, not that the catalogue was delisted). New scrapers that override `create_diffjson_stock_updates` must preserve this guard.
- Do **not** exclude tasting-kit / sampler / taster-pack products by default. Instead, extract them and let `_apply_product_flags` flag them with `is_tasting_kit = true` and `requires_review = true` so they land in the admin review queue instead of being silently dropped. Only genuine equipment/services (`grinder`, `v60`, `subscription`, `gift-card`, …) should be excluded. See [`docs/KIT_REVIEW.md`](docs/KIT_REVIEW.md) for the full pipeline.

### When Adding New Scrapers

1. Create `src/kissaten/scrapers/<roaster_name>.py` (use a `shopify-scraper`, `squarespace-scraper`, or `non-shopify-scraper` skill when the platform matches)
2. Inherit from `BaseScraper`, implement async `scrape()`, return validated `CoffeeBean` objects
3. Register in `src/kissaten/scrapers/registry.py`
4. Add tests in `tests/unit/test_<roaster>.py`

## Data Flow & Updates

The pipeline is incremental, not full-reimport. Scrapers write per-bean JSON + diff artifacts into `data/roasters/<roaster>/<YYYYMMDD>/`; `kissaten refresh` applies them to the rw DuckDB, which is then validated and promoted to the prod DB. See [`docs/INCREMENTAL_DATABASE_UPDATES.md`](docs/INCREMENTAL_DATABASE_UPDATES.md).

## API Design

Routes live under `/v1/*` in `src/kissaten/api/main.py`: `/v1/search`, `/v1/roasters`, `/v1/beans/{roaster_slug}/{bean_slug}`, `/v1/origins` (+ regions/farms), `/v1/processes`, `/v1/varietals`, `/v1/tasting-note-categories` (+ `/v1/tasting-notes/{note}/details`), `/v1/stats`, `/v1/health`. Use Pydantic models for request/response. Public search must keep hiding `requires_review = true` rows unless `include_unreviewed = true` is passed.

## CLI

The `kissaten` CLI (Typer + rich) is defined in `src/kissaten/cli/main.py`. Real commands include: `scrape`, `test-scraper`, `run-all-scrapers`, `refresh`, `refresh-media`, `validate-db`, `serve`, `dev`, `show-bean`, `list-sessions`, `list-scrapers`, `scraper-info`, `cache-stats`/`cache-cleanup`/`cache-clear`, `categorize-processing`/`categorize-varietals`/`categorize-tasting-notes`/`categorize-all`, `validate-mappings`, `deduplicate-regions`, `deduplicate-mappings`, `apply-review-decisions`.

## Testing

Run with `uv run pytest` (config in `pyproject.toml`, `asyncio_mode = "auto"`). Test files live flat in `tests/` (integration-style API tests) and `tests/unit/` (scraper/unit tests); DB isolation is handled by `tests/conftest.py` — never open the real DBs from a test without `KISSATEN_ALLOW_PRODUCTION_DB=1` (use the temp DB instead). Add tests when creating API endpoints, CLI commands, validation/transformation logic, or fixing bugs.

## Common Tasks for AI Assistants

### Scheduling Scrapers

`kissaten run-all-scrapers` supports `--num-batches N --batch-index I --date YYYY-MM-DD` to split the workload across hourly cron ticks with a date-seeded shuffle (same order all day, fresh order each day). The recommended schedule scrapes hourly but only runs `kissaten refresh --incremental` and `kissaten validate-db` on every 3rd tick (batch indices 3, 6, 9, 12, 15 — hours 07, 10, 13, 16, 19 UTC); the other ticks pass `--no-refresh --no-validate`. Each refresh+validate still runs as a subprocess inside the same traced batch span as the scrapes. Full cron examples, the validation check set, and tradeoffs are in [`docs/SCHEDULING.md`](docs/SCHEDULING.md).

### Validating a database before promotion

`kissaten validate-db [--db-path <path>] [--update-snapshot]` runs eight check categories against a DuckDB file (default `data/rw_kissaten.duckdb`): volume drift vs last-known-good snapshot, required-field nulls, referential integrity, normalization invariants (price→price_usd, currency_rates), 24h freshness, FTS index health (source-table divergence vs `coffee_beans`, FTS index artifacts `fts_main_coffee_beans_fts_source.docs/terms` populated, and a `match_bm25` probe returning at least one hit), in-stock drift vs snapshot (mass `in_stock` flips), and last-batch health (`data/last_batch_results.json` written by `run-all-scrapers`; ≥50% scraper failures blocks promotion). Each check is its own logfire span; pass/fail events carry the offending count. Exits 1 on any failure so the rw DB is not promoted to production.

### Reviewing tasting kits before promotion

Curated sampler/taster-pack products are flagged `is_tasting_kit` / `requires_review` at scrape time and hidden from public search until an admin approves them. The admin approves/rejects them in the frontend, then `kissaten apply-review-decisions --from-db <path>` (optionally `--update-db` to also write `requires_review=false` straight into the rw DuckDB, skipping the wait for a refresh) writes the decisions as `*.review.diffjson` next to the bean's JSON in its session folder (`data/roasters/<roaster>/<session>/<slug>_<hash8>.review.diffjson`); the next `kissaten refresh` picks those up (recursive `data/**/*.diffjson` glob) and flips `requires_review` to `false` before promotion. See [`docs/KIT_REVIEW.md`](docs/KIT_REVIEW.md).

### When Modifying Schemas

1. Update Pydantic models in `src/kissaten/schemas/`
2. Run database migrations if needed
3. Update API response models
4. Update frontend TypeScript types
5. Add/update tests

When touching the bean schema, remember the two review-flag columns
`is_tasting_kit` (persistent category flag for curated sampler/taster kits) and
`requires_review` (gate flag that hides a product from public search until an
admin approves it). Both live on `CoffeeBean` / `CoffeeBeanDiffUpdate` /
`CoffeeBeanOptional` and in the DuckDB `coffee_beans` table; new schemas and
diffs must propagate them, and public search must keep hiding
`requires_review = true` rows unless `include_unreviewed = true`. See
[`docs/KIT_REVIEW.md`](docs/KIT_REVIEW.md).

This document should be updated as the project evolves and new patterns emerge.

<!-- OPENWIKI:START -->

## OpenWiki

This repository has a generated `openwiki/` evidence index. It is optional just-in-time context, not required startup reading.

- Treat source code and tests as authoritative. A brief's unknowns and review items are verification gaps, not automatic requirements.
- Prefer the narrowest quiet validation that proves the changed behavior. Preserve complete failure output.

The scheduled OpenWiki GitHub Actions workflow refreshes the repository wiki. Do not hand-edit generated OpenWiki pages unless explicitly asked; prefer updating source code/docs and letting OpenWiki regenerate.

<!-- OPENWIKI:END -->