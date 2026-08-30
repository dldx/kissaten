---
type: "Reference"
title: "Architecture Overview"
description: "Three-layer system design (SvelteKit frontend, FastAPI backend, DuckDB data layer), data flow from scraping to API, key source files, and external dependencies, with cross-links to Coffee Domain Concept and Design & UX pages."
tags: [architecture, system-design, data-flow, fastapi, sveltekit, duckdb, cross-references]
verified:
  - by: openwiki/0.4.3
    at: 2026-08-29T13:59:13.975Z
sources:
  - id: openwiki-source-fc66ecb62ab86634b3050163
    resource: repo://env.example
  - id: openwiki-source-daf061cdbd9bf52b51668564
    resource: repo://frontend/src/routes/(main)/%2Blayout.svelte
  - id: openwiki-source-d889e404ccb79052966d2072
    resource: repo://src/kissaten/ai/validation_gate.py
  - id: openwiki-source-b6db435ba1198be65f340e6b
    resource: repo://src/kissaten/api/db.py
  - id: openwiki-source-9735fcc3e14d5d9974206d6d
    resource: repo://src/kissaten/api/main.py
  - id: openwiki-source-518e35e959773aac7710e8ac
    resource: repo://src/kissaten/cli/main.py
  - id: openwiki-source-1ae98847b5395e25f2b3c8c2
    resource: repo://src/kissaten/scrapers/registry.py
  - id: openwiki-source-d09264b76831d20864b449c9
    resource: repo://src/kissaten/services/geocoding.py
generated: { by: "openwiki/0.4.3", at: "2026-08-29T13:59:13.975Z" }
---

# Architecture Overview

## System Design

Kissaten is a three-layer coffee bean discovery platform:

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (SvelteKit)               │
│  Routes: search, roasters, origins, flavours,       │
│  tasting wizard, brew assistant, vault               │
├─────────────────────────────────────────────────────┤
│                    API (FastAPI)                      │
│  33+ endpoints + 4 sub-routers (AI search, brew,     │
│  FX, podcasts)                                       │
├─────────────────────────────────────────────────────┤
│               Data Layer (DuckDB + JSON)              │
│  coffee_beans, origins, roasters, tasting_notes,     │
│  currency_rates, varietal_mappings, etc.             │
├─────────────────────────────────────────────────────┤
│               Scraping & AI Pipeline                  │
│  150+ scrapers → AI extraction/categorisation →      │
│  validation gates → DuckDB                            │
└─────────────────────────────────────────────────────┘
```

The layers map cleanly onto the top-level source directories: `frontend/` (SvelteKit 5, runes mode), `src/kissaten/api/` (FastAPI app plus DuckDB layer), `src/kissaten/scrapers/` and `src/kissaten/ai/` (scraping and AI enrichment pipeline), and `src/kissaten/database/` (static canonical reference data). The frontend never touches DuckDB directly for catalog data — it talks to the FastAPI layer; only user-scoped data (tasting sessions, saved beans, custom beans, brew recipes) uses the local-first sync path to Turso/libSQL.

## Data Flow

<!-- openwiki: mermaid parse failed and this diagram was converted to a text fence so it does not break rendering. Fix the diagram source and restore the mermaid fence. Parser error: Heuristic: an unescaped angle bracket inside a label breaks rendering; rephrase the label. -->
```text
flowchart TD
    subgraph Scrape["Scraping & AI pipeline"]
        S1["Per-roaster scrapers<br/>(curl_cffi shim + BeautifulSoup4 / Playwright)"]
        S2["CoffeeDataExtractor<br/>(Gemini 2.5 Flash / Lite)"]
        S3["AI categorisers<br/>(process, varietal, tasting notes, regions)"]
        S4["validation_gate.py<br/>mapping consistency check"]
        S5["JSON files under<br/>data/roasters/roaster/session/"]
        S6["Review gate<br/>is_tasting_kit + requires_review"]
    end
    subgraph Store["DuckDB data layer"]
        D1["rw_kissaten.duckdb<br/>(refresh, read-write)"]
        D2["kissaten.duckdb<br/>(API, read-only)"]
    end
    subgraph Serve["Serving"]
        A1["FastAPI endpoints<br/>search, facets, pricing, geography"]
        F1["SvelteKit frontend<br/>local-first user data via Dexie/Turso"]
    end
    S1 --> S2 --> S3 --> S4 --> S5 --> S6 --> D1
    D1 -- "cp swap" --> D2
    D2 --> A1 --> F1
```

*Diagram: end-to-end data flow from per-roaster scraping through AI enrichment, validation, JSON persistence, the DuckDB read-write/read-only split, and out to the FastAPI/SvelteKit serving layers.*

1. **Scraping**: Per-roaster scrapers (curl_cffi via a thin shim, plus BeautifulSoup4 or Playwright) fetch product pages and extract raw bean data.
2. **AI Extraction**: `CoffeeDataExtractor` (Gemini 2.5 Flash/Lite) processes HTML and/or screenshots into structured `CoffeeBean` Pydantic models. Translates foreign-language pages when needed.
3. **Categorisation**: AI categorisers standardise processing methods, varietals, tasting notes, and regions using mapping files in `src/kissaten/database/`.
4. **Validation**: `validation_gate.py` checks mapping consistency (no conflicting duplicates) before data enters DuckDB. `kissaten deduplicate-mappings` collapses redundant case-variant duplicate mappings; genuine conflicts are left for humans (see [data/name-mappings.md](../data/name-mappings.md)).
5. **Storage**: Validated beans are saved as JSON under `data/roasters/<roaster>/<session>/` (with sidecar `*.diffjson` update files, including `*.review.diffjson` from the tasting-kit approval flow). DuckDB loads these incrementally via checksum-based diffing; `price_options` bag variants populate the `largest_bag` pricing CTE.
6. **Review gate (2026-08)**: tasting kits/samplers are flagged `is_tasting_kit` + `requires_review` at scrape time; they are hidden from public search until an admin approves them via the frontend queue and `kissaten apply-review-decisions` writes a review diffjson (see [operations/tasting-kit-review-pipeline.md](../operations/tasting-kit-review-pipeline.md)).
7. **API**: FastAPI serves DuckDB data with full-text search, faceted filtering, relevance scoring, largest-bag pricing, and location exploration (`/v1/roasted-in/{slug}`).
8. **Frontend**: SvelteKit consumes the API, with local-first sync (Dexie/IndexedDB ↔ Turso/libSQL via Drizzle) for user data — tasting sessions, saved beans, custom beans, and brew recipes. See [frontend/sync-system.md](../frontend/sync-system.md) for the full sync architecture.

### DuckDB connection lifecycle

`src/kissaten/api/db.py` opens a single module-level `conn` at import time, with the mode selected by `KISSATEN_USE_RW_DB`:

- **Read-write mode** (`KISSATEN_USE_RW_DB=1`, used by `kissaten refresh` and the test suite): permissive config `{}` so `load_coffee_data` can use DuckDB's `read_json`/`glob`; runs all `ensure_*` migrations.
- **API mode** (default, `kissaten serve`): opens `data/kissaten.duckdb` read-only, loads the FTS extension (process-local, works read-only), then hardens with `SET enable_external_access = false`. No migrations run — the production DB is produced by `kissaten refresh`.

The production-DB safety guard (`_check_production_db_guard`) refuses to open `kissaten.duckdb` or `rw_kissaten.duckdb` with a writable config unless `KISSATEN_ALLOW_PRODUCTION_DB=1` is set. The API config satisfies the guard because `enable_external_access=False` is a non-writable config, so the guard is effectively an opt-in mechanism for tests and ad-hoc scripts that target the real databases.

## Key Source Files

| Area | File | Purpose |
|---|---|---|
| API main | `src/kissaten/api/main.py` | 33+ FastAPI endpoints, app lifecycle |
| Database | `src/kissaten/api/db.py` | DuckDB connection, schema, queries, safety guard |
| CLI | `src/kissaten/cli/main.py` | 19 Typer commands (scrape, serve, refresh, validate-db, apply-review-decisions, deduplicate-mappings, etc.) |
| Scraper base | `src/kissaten/scrapers/base.py` | ~1,800-line BaseScraper ABC |
| Shopify base | `src/kissaten/scrapers/shopify_base.py` | Shopify-specific scraper base |
| Scraper registry | `src/kissaten/scrapers/registry.py` | `@register_scraper` decorator + singleton |
| AI extractor | `src/kissaten/ai/extractor.py` | Gemini-powered extraction from HTML/images |
| AI search | `src/kissaten/ai/search_agent.py` | Natural language → structured search params |
| Brew assistant | `src/kissaten/api/brew_assistant.py` | AI pour-over/espresso recipe generator |
| BeanConqueror | `src/kissaten/api/beanconqueror_share.py` | Protobuf share-link generator |
| Schemas | `src/kissaten/schemas/coffee_bean.py` | Core `CoffeeBean` Pydantic model |
| Dedup | `src/kissaten/dedup/` | Farm-name canonicalisation pipeline |
| Geocoding | `src/kissaten/services/geocoding.py` | OpenCage geocoding with file cache |
| Frontend API | `frontend/src/lib/api.ts` | TypeScript API client (~53K lines) |

## Backend Package Structure

```
src/kissaten/
├── ai/            # AI modules (extractor, categorisers, search agent, validation)
├── api/           # FastAPI app, DB, sub-routers (ai_search, brew, fx, podcasts)
│   └── proto/     # Protobuf definitions for BeanConqueror share
├── cache/         # AI search cache, media insights cache (DuckDB-backed)
├── cli/           # Typer CLI with Rich output
├── database/      # Static data: mappings, lexicons, CSVs, region JSONs
├── dedup/         # Farm deduplication (normalise → fuzzy match → cluster → TUI)
├── schemas/       # Pydantic models for beans, roasters, search, API responses
├── services/      # Geocoding service (OpenCage)
└── scrapers/      # 150+ roaster scrapers + base classes + registry
```

## Frontend Structure

```
frontend/src/
├── routes/
│   ├── (main)/        # Primary layout: search, roasters, origins, flavours, vault, brew-assistant
│   ├── (no-layout)/   # Standalone pages: stickers, etc.
│   ├── auth/          # Authentication (magic-link email via better-auth)
│   ├── og/            # Open Graph image generation
│   └── sitemap*.xml/  # SEO sitemaps
├── lib/
│   ├── api.ts         # Central API client
│   ├── api/           # Remote API modules (custom beans, etc.)
│   ├── components/     # UI components (CoffeeBeanCard, TastingWizard, etc.)
│   ├── sync/           # Local-first sync (Dexie ↔ server)
│   ├── tasting/        # Tasting wizard logic
│   ├── stores/         # Svelte stores for state management
│   ├── schemas/        # TypeScript schemas (bean form, etc.)
│   ├── utils/          # Utilities (CF image, etc.)
│   ├── server/         # Server-side utilities
│   ├── hooks/          # Svelte hooks
│   ├── config/         # Frontend configuration
│   ├── db/             # Dexie (IndexedDB) local database + reactive triggers
│   ├── types/          # TypeScript types
│   └── services/       # Frontend services
├── hooks.server.ts    # Sentry, auth middleware
├── hooks.client.ts    # Client-side hooks
└── service-worker.ts  # PWA service worker
```

The `(main)/+layout.svelte` is the shared primary layout. It renders the sticky header with the primary navigation (`Beans` → `/search`, `Origins` → `/origins`, `Varietals` → `/varietals`, `Processes` → `/processes`, `Roasters` → `/roasters`, `Flavours` → `/flavours`), the currency selector, theme toggle, and auth-status button. It also boots the local-first sync on mount (`runGlobalSync({ silent: true })`), re-syncs when the device comes online, and runs a `verify-then-fix` sync when the tab regains focus after being hidden for more than an hour — wiring the architecture's serving layer to the sync system documented in [frontend/sync-system.md](../frontend/sync-system.md).

## External Dependencies

- **Google Gemini**: AI extraction, categorisation, search, brew recipes, podcast tagging
- **OpenCage API**: Region geocoding (`OPENCAGE_API_KEY`)
- **Sentry**: Error monitoring (frontend + backend)
- **Logfire**: Trace-level scraper observability
- **Cloudflare Images**: Image CDN for resized product images
- **Turso (libSQL)**: Server-side user data (vault, saved beans) via Drizzle ORM
- **BeanConqueror**: Coffee app integration via share links

## Environment Variables

Key variables (defined in `.env`, see `env.example` for placeholders):
- `GOOGLE_API_KEY` — Google Gemini API access
- `OPENCAGE_API_KEY` — OpenCage geocoding
- `SENTRY_DSN` — Sentry error tracking
- `HTTP_PROXY` / `HTTPS_PROXY` — Proxy for scraping
- `KISSATEN_DATABASE_PATH` — Override DuckDB path (used in tests)
- `KISSATEN_USE_RW_DB` — Use read-write DuckDB
- `KISSATEN_ALLOW_PRODUCTION_DB` — Bypass production DB safety guard
- `BREW_JWT_SECRET` — Secret for signing/verifying brew session JWTs between SvelteKit and FastAPI

## Domain Concepts

The data flow above operates on a set of specialty-coffee domain concepts. Each maps to schema fields in the `CoffeeBean` model (see [data/data-model.md](../data/data-model.md)) and is surfaced through dedicated API endpoints and frontend routes. The concept pages (under `/openwiki/concepts/`) document the domain knowledge behind each field:

- **Processing methods** — washed, natural, honey, anaerobic, etc.; standardised by `processing_methods_mappings.json` and exposed via `/v1/processes` and the `/processes` route. → [concepts/processing-methods.md](../concepts/processing-methods.md)
- **Varietals** — Bourbon, Gesha, Catuai, etc.; canonicalised by the varietal categoriser and exposed via `/v1/varietals` and the `/varietals` route. → [concepts/varietals.md](../concepts/varietals.md)
- **Origin geography** — countries, regions, farms, elevations, the coffee belt; modelled in the `origins` table and exposed via the `/v1/origins/...` hierarchy and `/origins` route. → [concepts/origin-geography.md](../concepts/origin-geography.md)
- **Tasting notes** — three-tier taxonomy; categorised by the tasting-note categoriser and exposed via `/v1/tasting-note-categories` and the `/flavours` route. → [concepts/tasting-note-taxonomy.md](../concepts/tasting-note-taxonomy.md)
<!-- openwiki: broken internal link [../concepts/roast-levels.md] file "../concepts/roast-levels.md" does not exist. Fix the href or restore the target, then delete this comment. -->
- **Roast levels** — Extra-Light through Dark enum; surfaced as a search facet and on bean detail pages. → [concepts/roast-levels.md](../concepts/roast-levels.md)
- **Cupping scores** — 70–100 float; a searchable filter (`min_cupping_score`/`max_cupping_score`) and sort key. → [concepts/cupping-scores.md](../concepts/cupping-scores.md)
- **Price transparency** — `fob_price`, `farm_gate_price`, `price_paid_to_producer`; captured per origin and used in transparency surfacing. → [concepts/price-transparency.md](../concepts/price-transparency.md)
- **Decaffeination** — `is_decaf` boolean; a dedicated search facet. → [concepts/decaffeination.md](../concepts/decaffeination.md)

## Design & UX

The serving layer implements several product design patterns that turn the domain concepts above into discovery experiences. Each pattern references the frontend components and API endpoints that implement it; the design pages (under `/openwiki/design/`) document the rationale:

- **Guided discovery** — explore by flavour, process, or varietal from the home page and dedicated routes. → [design/guided-discovery.md](../design/guided-discovery.md)
- **Faceted filtering** — the `/search` route combines full-text search, wildcard/boolean tasting-note filters, and multi-dimensional facets (origin, roaster, process, varietal, price, roast level, availability, review/kit status) backed by `GET /v1/search`. → [design/faceted-filtering.md](../design/faceted-filtering.md)
- **Origin exploration** — the `/origins` route and `/v1/origins/...` hierarchy let users drill from country → region → farm. → [design/origin-exploration.md](../design/origin-exploration.md)
<!-- openwiki: broken internal link [../design/bean-detail-ia.md] file "../design/bean-detail-ia.md" does not exist. Fix the href or restore the target, then delete this comment. -->
- **Bean detail information architecture** — the `[roaster_name]/[bean_name]` route surfaces origin, processing, tasting, pricing, and recommendation data. → [design/bean-detail-ia.md](../design/bean-detail-ia.md)
- **Roaster exploration** — the `/roasters` route and roaster detail pages render the uniqueness report and location-based browsing (`/roasted-in/{slug}`). → [design/roaster-exploration.md](../design/roaster-exploration.md)
<!-- openwiki: broken internal link [../design/analytics.md] file "../design/analytics.md" does not exist. Fix the href or restore the target, then delete this comment. -->
- **Analytics** — database statistics and insights dashboards surfaced via `/v1/stats` and roaster uniqueness reports. → [design/analytics.md](../design/analytics.md)
