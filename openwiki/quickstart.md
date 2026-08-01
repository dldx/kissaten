---
type: "Reference"
title: "Kissaten — Coffee Bean Discovery Platform"
description: "Entry point for the Kissaten code wiki: full-stack coffee bean discovery platform that scrapes 150+ roasters, enriches via AI, stores in DuckDB, and serves a SvelteKit frontend."
---

# Kissaten — Coffee Bean Discovery Platform

Kissaten is a full-stack coffee bean discovery platform that scrapes bean data from 150+ specialty coffee roasters worldwide, processes it through an AI-assisted validation pipeline, stores it in DuckDB, and serves a modern SvelteKit frontend for searching, browsing, and exploring coffee beans.

## What This Wiki Covers

| Section | Page | Description |
|---|---|---|
| Architecture | [architecture/overview.md](architecture/overview.md) | System design, backend/frontend/data layers, data flow |
| Scrapers | [scrapers/scraping-system.md](scrapers/scraping-system.md) | BaseScraper, Shopify base, registry, how to add scrapers |
| API & Backend | [api/backend-api.md](api/backend-api.md) | FastAPI endpoints, DuckDB layer, sub-routers, schemas |
| API & Backend | [api/roaster-uniqueness.md](api/roaster-uniqueness.md) | Multi-dimensional roaster uniqueness algorithm: lift, percentile, threshold gates, four dimensions, frontend rendering |
| AI Pipeline | [ai/ai-pipeline.md](ai/ai-pipeline.md) | AI extractors, categorizers, search agent, validation gate, caching |
| Data Model | [data/data-model.md](data/data-model.md) | CoffeeBean schema, DuckDB tables, mappings, taste lexicon |
| Data | [data/name-mappings.md](data/name-mappings.md) | All canonical name mappings: processing methods, varietals, tasting notes, farms, regions, validation |
| Frontend | [frontend/frontend.md](frontend/frontend.md) | SvelteKit routes, API client, sync overview, tasting wizard, stores |
| Frontend | [frontend/sync-system.md](frontend/sync-system.md) | Dexie↔Turso/libSQL local-first sync: architecture, protocol, conflict resolution, verification |
| Operations | [operations/operations.md](operations/operations.md) | CLI, scheduling, DB validation, testing, deployment, CI |

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, DuckDB, Polars, Pydantic v2, curl_cffi (scraper HTTP, via a thin shim), httpx (API/services), Playwright, BeautifulSoup4, Typer, Rich
- **AI**: PydanticAI + Google Gemini (extraction, categorization, search), OpenCage (geocoding)
- **Frontend**: SvelteKit 5 (runes mode), shadcn-svelte, Tailwind CSS v4, TypeScript, Bun, Threlte/Three.js
- **Database**: DuckDB (analytical), JSON (raw scraped data), Parquet (exports)
- **Infra**: uv (Python), Bun (JS), Sentry, Logfire, nginx, systemd

## Quick Setup

```bash
# Backend
uv sync
uv run python -m kissaten.cli.main dev --frontend   # starts API + frontend

# Or separately:
uv run python -m kissaten.cli.main serve --reload    # API at :8000
cd frontend && bun install && bun run dev             # Frontend at :5173
```

API docs at `http://localhost:8000/docs`.

## First-Time Data

```bash
uv run python -m kissaten.cli.main list-scrapers
uv run python -m kissaten.cli.main scrape <scraper_name>
uv run python -m kissaten.cli.main refresh           # load scraped JSON into DuckDB
```

Scraped data lives under `data/roasters/<roaster>/<session_date>/`. DuckDB files are at `data/kissaten.duckdb` (read-only) and `data/rw_kissaten.duckdb` (read-write).

## Key Concepts

- **Scrapers** are per-roaster modules under `src/kissaten/scrapers/`. Most inherit from `BaseScraper` or `ShopifyJsonScraper`. A registry auto-discovers them via decorators.
- **AI pipeline** enriches scraped data: extraction from HTML/screenshots, categorization of processing methods/varietals/tasting notes, region geocoding, and validation gates for mapping consistency.
- **DuckDB** is the primary analytical store. The API loads JSON data incrementally via checksum-based diffing.
- **Frontend** is a SvelteKit app with routes for search, roasters, origins, flavours, a tasting wizard, brew assistant, and a user vault.
- **CLI** (`kissaten` command) orchestrates scraping, database refresh, validation, server lifecycle, and maintenance tasks.

## Important Conventions

- **Never hardcode coffee bean values in scrapers** — extract everything from HTML.
- **Never open production DuckDB files from tests** — `tests/conftest.py` redirects to a temp DB. A safety guard in `src/kissaten/api/db.py` blocks accidental writes.
- **AI models**: All use PydanticAI with Google Gemini, `thinking_budget=0` for cost efficiency.
- **Scheduling**: 150+ scrapers run in 16 hourly batches (06:00–21:00 UTC) with a date-seeded shuffle.
- **British English**: All documentation, code comments, UI copy, and user-facing text must use British English spelling and conventions (e.g. "flavour", "colour", "organise", "optimise").
