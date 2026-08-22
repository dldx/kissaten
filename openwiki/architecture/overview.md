---
type: "Reference"
title: "Architecture Overview"
description: "Three-layer system design (SvelteKit frontend, FastAPI backend, DuckDB data layer), data flow from scraping to API, key source files, and external dependencies."
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
│  30+ main-app endpoints + 4 sub-routers (AI search,  │
│  brew, FX, podcasts)                                  │
├─────────────────────────────────────────────────────┤
│               Data Layer (DuckDB + JSON)              │
│  coffee_beans, origins, roasters, tasting_notes,     │
│  currency_rates, varietal_mappings, etc.             │
├─────────────────────────────────────────────────────┤
│               Scraping & AI Pipeline                  │
│  200+ scrapers → AI extraction/categorization →      │
│  validation gates → DuckDB                            │
└─────────────────────────────────────────────────────┘
```

## Data Flow

1. **Scraping**: Per-roaster scrapers (curl_cffi via a thin shim, plus BeautifulSoup4 or Playwright) fetch product pages and extract raw bean data.
2. **AI Extraction**: `CoffeeDataExtractor` (Gemini 2.5 Flash/Lite) processes HTML and/or screenshots into structured `CoffeeBean` Pydantic models. Translates foreign-language pages when needed.
3. **Categorization**: AI categorizers standardize processing methods, varietals, tasting notes, and regions using mapping files in `src/kissaten/database/`.
4. **Validation**: `validation_gate.py` checks mapping consistency (no conflicting duplicates) before data enters DuckDB.
5. **Storage**: Validated beans are saved as JSON under `data/roasters/<roaster>/<session>/`. DuckDB loads these incrementally via checksum-based diffing.
6. **API**: FastAPI serves DuckDB data with full-text search, faceted filtering, and relevance scoring.
7. **Frontend**: SvelteKit consumes the API, with local-first sync (Dexie/IndexedDB ↔ Turso/libSQL via Drizzle) for user data — tasting sessions, saved beans, custom beans, and brew recipes. See [frontend/sync-system.md](../frontend/sync-system.md) for the full sync architecture.

## Key Source Files

| Area | File | Purpose |
|---|---|---|
| API main | `src/kissaten/api/main.py` | 30+ main-app FastAPI endpoints + 4 sub-routers, app lifecycle |
| Database | `src/kissaten/api/db.py` | DuckDB connection, schema, queries, safety guard |
| CLI | `src/kissaten/cli/main.py` | 17 top-level Typer commands (plus a `categorize` sub-app) |
| Scraper base | `src/kissaten/scrapers/base.py` | ~1,800-line BaseScraper ABC |
| Shopify base | `src/kissaten/scrapers/shopify_base.py` | Shopify-specific scraper base |
| Scraper registry | `src/kissaten/scrapers/registry.py` | `@register_scraper` decorator + singleton |
| AI extractor | `src/kissaten/ai/extractor.py` | Gemini-powered extraction from HTML/images |
| AI search | `src/kissaten/ai/search_agent.py` | Natural language → structured search params |
| Brew assistant | `src/kissaten/api/brew_assistant.py` | AI pour-over/espresso recipe generator |
| BeanConqueror | `src/kissaten/api/beanconqueror_share.py` | Protobuf share-link generator |
| Schemas | `src/kissaten/schemas/coffee_bean.py` | Core `CoffeeBean` Pydantic model |
| Dedup | `src/kissaten/dedup/` | Farm-name canonicalization pipeline |
| Geocoding | `src/kissaten/services/geocoding.py` | OpenCage geocoding with file cache |
| Frontend API | `frontend/src/lib/api.ts` | TypeScript API client (~1,850 lines) |

## Backend Package Structure

```
src/kissaten/
├── ai/            # AI modules (extractor, categorizers, search agent, validation)
├── api/           # FastAPI app, DB, sub-routers (ai_search, brew, fx, podcasts)
│   └── proto/     # Protobuf definitions for BeanConqueror share
├── cache/         # AI search cache, media insights cache (DuckDB-backed)
├── cli/           # Typer CLI with Rich output
├── database/      # Static data: mappings, lexicons, CSVs, region JSONs
├── dedup/         # Farm deduplication (normalize → fuzzy match → cluster → TUI)
├── schemas/       # Pydantic models for beans, roasters, search, API responses
├── services/      # Geocoding service (OpenCage)
├── scrapers/      # 227 registered roaster scrapers + base classes + registry
```

## Frontend Structure

```
frontend/src/
├── routes/
│   ├── (main)/        # Primary layout: search, roasters, origins, flavours, processes, varietals, tasting, brew-assistant, vault, profile, admin, login, roasted-in
│   ├── (no-layout)/   # Standalone pages: stickers, labels, flavour-image
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

## External Dependencies

- **Google Gemini**: AI extraction, categorization, search, brew recipes, podcast tagging
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
