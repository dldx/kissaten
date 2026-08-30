---
type: "Reference"
title: "Kissaten — Coffee Bean Discovery Platform"
description: "Entry point for the Kissaten wiki: routes readers through Code & Architecture, Coffee Domain Concepts, and Design & UX, with quick setup commands, first-time data instructions, key conventions, and the tech stack."
tags: [quickstart, entry-point, architecture, coffee-domain, design-ux, setup]
verified:
  - by: openwiki/0.4.3
    at: 2026-08-29T13:59:13.975Z
sources:
  - id: openwiki-source-8037e2358a2c4f9b2c722a11
    resource: repo://AGENTS.md
  - id: openwiki-source-668797a390c0d949bb6ac91d
    resource: repo://QUICKSTART.md
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
  - id: openwiki-source-1ae98847b5395e25f2b3c8c2
    resource: repo://src/kissaten/scrapers/registry.py
generated: { by: "openwiki/0.4.3", at: "2026-08-29T13:59:13.975Z" }
---

# Kissaten — Coffee Bean Discovery Platform

Kissaten is a full-stack coffee bean discovery platform that scrapes bean data from specialty coffee roasters worldwide, processes it through an AI-assisted validation pipeline, stores it in DuckDB, and serves a modern SvelteKit frontend for searching, browsing, and exploring coffee beans.

This wiki covers three overlapping areas, and the pages link between them. Use the routing tables below to find the right entry point.

## Code & Architecture

| Section | Page | Description |
|---|---|---|
| Architecture | [architecture/overview.md](architecture/overview.md) | Three-layer system design (SvelteKit frontend, FastAPI backend, DuckDB data layer), data flow from scraping to API, key source files, and external dependencies |
| Scrapers | [scrapers/scraping-system.md](scrapers/scraping-system.md) | BaseScraper, Shopify base, registry, how to add scrapers |
| API & Backend | [api/backend-api.md](api/backend-api.md) | FastAPI endpoints, DuckDB layer, sub-routers, schemas |
| API & Backend | [api/roaster-uniqueness.md](api/roaster-uniqueness.md) | Multi-dimensional roaster uniqueness algorithm: lift, percentile, threshold gates, four dimensions, frontend rendering |
| AI Pipeline | [ai/ai-pipeline.md](ai/ai-pipeline.md) | AI extractors, categorizers, search agent, validation gate, caching |
| Data Model | [data/data-model.md](data/data-model.md) | CoffeeBean schema, DuckDB tables, mappings, taste lexicon |
| Data | [data/name-mappings.md](data/name-mappings.md) | All canonical name mappings: processing methods, varietals, tasting notes, farms, regions, validation |
| Frontend | [frontend/frontend.md](frontend/frontend.md) | SvelteKit routes, API client, sync overview, tasting wizard, stores |
| Frontend | [frontend/sync-system.md](frontend/sync-system.md) | Dexie↔Turso/libSQL local-first sync: architecture, protocol, conflict resolution, verification |
| Frontend | [frontend/email-notifications.md](frontend/email-notifications.md) | SMTP transport, branded email shell, admin digests, user-facing emails (roaster-implemented to voters) |
| Roasters | [roasters/index.md](roasters/index.md) | Roaster profiles: sustainability, equipment, philosophy, quirks for scraped UK roasters |
| Operations | [operations/operations.md](operations/operations.md) | CLI, scheduling, DB validation, testing, deployment, CI |

## Coffee Domain Concepts

These pages document the specialty coffee knowledge that underpins the database and map each domain concept to the schema fields, data files, AI modules, API endpoints, and frontend routes that implement it.

| Domain concept | Page | Maps to |
|---|---|---|
| Processing methods | [concepts/processing-methods.md](concepts/processing-methods.md) | `process` field in CoffeeBean/Bean, `processing_methods_mappings.json`, `ProcessCategorizer` AI module, `/v1/processes` + `/v1/processes/{slug}`, frontend processes route |
| Varietals | [concepts/varietals.md](concepts/varietals.md) | `variety` field, `coffee_varietals.json` (WCR reference), `varietal_mappings.json`, `VarietalCategorizer` AI module, `/v1/varietals`, frontend varietals route |
| Origin geography | [concepts/origin-geography.md](concepts/origin-geography.md) | `origins[]` array, `origins` DuckDB table, `/v1/origins` hierarchy, `region_mappings`, geocoding, frontend origins route |
| Roast levels & profiles | [concepts/roast-levels-profiles.md](concepts/roast-levels-profiles.md) | `RoastLevel` enum and `roast_profile` Literal, `roast_level`/`roast_profile` search filters, `RoastProfileBar` component |
| Cupping scores | [concepts/cupping-scores.md](concepts/cupping-scores.md) | `cupping_score` field (70–100 range), `avg_cupping_score` in RoasterDetailResponse, `cupping_score` sort option |
| Tasting note taxonomy | [concepts/tasting-note-taxonomy.md](concepts/tasting-note-taxonomy.md) | `tasting_notes` array, `taste_lexicon.json`, `tasting_notes_categorized.csv`, `TastingNoteCategorizer`/`TastingNoteSplitter`, `/v1/tasting-note-categories`, SunburstChart + FlavourProfileDonut |
| Price transparency | [concepts/price-transparency.md](concepts/price-transparency.md) | `fob_price`, `farm_gate_price`, `price_paid_to_producer`, `price_currency`, `importer_name`, `price_paid_for_green_coffee`, bean detail API |
| Decaffeination | [concepts/decaffeination.md](concepts/decaffeination.md) | `is_decaf` boolean, `is_decaf` search filter, frontend decaf surfacing |

## Design & UX Concepts

These pages document the product design decisions that make the database useful and reference the domain concepts they surface plus the frontend components and API endpoints that implement them.

| UX area | Page | Implements |
|---|---|---|
| Guided discovery | [design/guided-discovery.md](design/guided-discovery.md) | Home page journey, explore-by-flavour/process/varietal entry points, `CoffeeJourney` component, curated educational content |
| Faceted filtering | [design/faceted-filtering.md](design/faceted-filtering.md) | `SearchFilters` component, filter taxonomy (origin, roaster, process, varietal, roast level, roast profile, price, weight, elevation, in-stock, decaf, single-origin, tasting-kit), URL-driven state, `/v1/search` |
| Origin exploration | [design/origin-exploration.md](design/origin-exploration.md) | Country→region→farm drill-down, `GeographyBreadcrumb`, `ElevationMountainChart`, `RegionCard`, `FarmCard`, `OriginResultCard`, `/v1/origins` |
| Bean detail page | [design/bean-detail-page.md](design/bean-detail-page.md) | Information hierarchy, `SunburstChart`, `FlavourProfileDonut`, `RoastProfileBar`, tasting notes, origin traceability, price options, cupping score, recommendations, BeanConqueror share |
| Roaster exploration | [design/roaster-exploration.md](design/roaster-exploration.md) | Roasters listing, roaster detail with uniqueness report, roaster sticker wall, roasted-in location exploration, roaster-to-bean drill-down |
| Analytics & insights | [design/analytics-insights.md](design/analytics-insights.md) | `/v1/stats` endpoint, home page stats, `SunburstChart` flavour distribution, origin/process/varietal statistics, `InsightCard` |

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
- **DuckDB** is the primary analytical store. The API loads JSON data incrementally via checksum-based diffing. `price_options` (bag-size variants) power largest-bag pricing on search.
- **Tasting kits & review queue** — curated multi-coffee kits/samplers are extracted and flagged `is_tasting_kit` + `requires_review`; they stay out of public search until an admin approves them through the frontend review queue and `kissaten apply-review-decisions`. See [operations/tasting-kit-review-pipeline.md](operations/tasting-kit-review-pipeline.md).
- **Frontend** is a SvelteKit app with routes for search, roasters, origins, flavours, a tasting wizard, brew assistant, and a user vault.
- **CLI** (`kissaten` command) orchestrates scraping, database refresh, validation, server lifecycle, and maintenance tasks (including `apply-review-decisions` and `deduplicate-mappings`).

## Important Conventions

- **Never hardcode coffee bean values in scrapers** — extract everything from HTML.
- **Never open production DuckDB files from tests** — `tests/conftest.py` redirects to a temp DB. A safety guard in `src/kissaten/api/db.py` blocks accidental writes.
- **AI models**: All use PydanticAI with Google Gemini, `thinking_budget=0` for cost efficiency.
- **Scheduling**: 150+ scrapers run in 16 hourly batches (06:00–21:00 UTC) with a date-seeded shuffle.
- **British English**: All documentation, code comments, UI copy, and user-facing text must use British English spelling and conventions (e.g. "flavour", "colour", "organise", "optimise").
