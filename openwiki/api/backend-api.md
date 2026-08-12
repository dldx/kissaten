---
type: "Reference"
title: "Backend API & Database"
description: "FastAPI endpoints, DuckDB layer, sub-routers, Pydantic schemas, and protobuf share-link generation for the Kissaten backend."
---

# Backend API & Database

## FastAPI Application (`src/kissaten/api/main.py`)

The main FastAPI app exposes 30+ endpoints directly on `app` and mounts 4 sub-routers. All main-app paths are prefixed `/v1/` (plus `/health` and `/`). Key endpoint groups:

### Core Search & Browse
- `GET /v1/search` — Full-text search with faceted filtering (origin, roaster, process, varietal, price, roast level, availability) and relevance scoring
- `POST /v1/search/by-paths` — Fetch beans by roaster/bean path pairs
- `GET /v1/beans/{roaster_slug}/{bean_slug}` — Individual bean detail
- `GET /v1/beans/{roaster_slug}/{bean_slug}/recommendations` — Attribute-based bean recommendations
- `GET /v1/roasters` — List all roasters with metadata
- `GET /v1/roasters/{roaster_slug}` — Roaster profile, beans, and multi-dimensional [roaster uniqueness report](roaster-uniqueness.md)
- `GET /v1/roaster-locations` — Roaster location listings
- `GET /v1/roasted-in/{slug}` — Roaster-location detail ("roasted in" exploration)
- `GET /v1/stats` — Database statistics and analytics
- `GET /v1/country-codes` — ISO country code reference

### Origin & Geography
- `GET /v1/origins` — Coffee origins with hierarchy (country → region → farm)
- `GET /v1/origins/{country_code}` — Country detail
- `GET /v1/origins/{country_code}/regions` — Regions within a country
- `GET /v1/origins/{country_code}/{region_slug}` — Region detail
- `GET /v1/origins/{country_code}/{region_slug}/{farm_slug}` — Farm detail
- `GET /v1/search/origins` — Origin search

### Processes & Varietals
- `GET /v1/processes` — Processing method index
- `GET /v1/processes/{process_slug}` — Process detail
- `GET /v1/processes/{process_slug}/beans` — Beans for a process
- `GET /v1/varietals` — Varietal index
- `GET /v1/varietals/{varietal_slug}` — Varietal detail
- `GET /v1/varietals/{varietal_slug}/beans` — Beans for a varietal

### Tasting & Flavours
- `GET /v1/tasting-note-categories` — Three-tier tasting-note category index
- `GET /v1/search/by-tasting-category` — Beans for a tasting-note category
- `GET /v1/tasting-notes/{note_text}/details` — Tasting-note detail
- `GET /v1/flavour-images` — Flavour images for UI display

### BeanConqueror Share
- `GET /v1/beans/{roaster_slug}/{bean_slug}/beanconquerer-link` — Generate a BeanConqueror app share link
- `POST /v1/custom-beans/beanconquerer-link` — Share link for a user-created custom bean

### Roaster Uniqueness Report
The roaster detail endpoint (`GET /v1/roasters/{roaster_slug}`) computes a multi-dimensional [roaster uniqueness report](roaster-uniqueness.md) that identifies where a roaster most over-indexes vs the global average across flavour, origin, process, and varietal dimensions. See [roaster-uniqueness.md](roaster-uniqueness.md) for the full algorithm, threshold gates, SQL queries, and Pydantic models.

## Sub-Routers

### AI Search (`src/kissaten/api/ai_search.py`)
9 endpoints under `/v1/ai/*`:
- `POST /v1/ai/extract` — Image-based bean extraction (Gemini analyses product screenshots)
- `POST /v1/ai/imagesearch` — Image-based natural language search
- `POST /v1/ai/search` — Natural language search (translates queries to structured search params)
- `POST /v1/ai/search/redirect` — Search returning a redirect to a results URL
- `GET /v1/ai/health` — AI search health
- `GET /v1/ai/cache/stats`, `POST /v1/ai/cache/cleanup`, `DELETE /v1/ai/cache` — Cache management
- `POST /v1/ai/feedback` — Thumbs up/down feedback on search results

The AI search agent uses keyword-based context filtering to send only relevant database entries to the model (see [ai/ai-pipeline.md](../ai/ai-pipeline.md) § Search Architecture v2).

### Brew Assistant (`src/kissaten/api/brew_assistant.py`)
- `POST /v1/brew-assistant/recipe` — Generates personalized pour-over/espresso recipes using PydanticAI + Gemini, considering bean attributes and user equipment

### FX / Currency (`src/kissaten/api/fx.py`)
4 endpoints under `/v1/*`:
- `GET /v1/currencies` — List supported currencies with latest rates (10-minute response cache)
- `GET /v1/convert` — Convert an amount between currencies
- `POST /v1/currencies/update` — Update/refresh rates (backed by `currency_rates` DuckDB table)
- `POST /v1/currencies/refresh` — Force-refresh rates

### Podcasts (`src/kissaten/api/podcasts.py` + `podcast_db.py`)
- Full-text search over podcast transcripts (separate `podcasts.duckdb`)
- AI-powered reranking (Jina AI + Gemini)
- Podcast tagging via `PodcastTagger` (see [ai/ai-pipeline.md](../ai/ai-pipeline.md))

## DuckDB Layer (`src/kissaten/api/db.py`)

### Connection Management
- Single DuckDB connection (DuckDB is single-writer, multi-reader)
- **Two modes** selected by `KISSATEN_USE_RW_DB`:
  - **RW mode** (CLI refresh, tests): read-write connection, permissive config for `read_json`/glob, runs all `ensure_*` migrations at module load.
  - **API mode** (`kissaten serve`): opens the production DB with `read_only=True` via `_open_connection()` — a defence-in-depth measure that prevents WAL creation and buffer-pool corruption during the `cp rw_kissaten.duckdb kissaten.duckdb` swap-while-running workflow. No `ensure_*` migrations run; instead `_api_mode_schema_warnings()` performs read-only assertions and logs warnings if the schema is behind. DuckDB refuses to open a *missing* file read-only, so `_open_connection()` creates an empty DB first if needed.
- **Production safety guard**: Refuses to open `data/rw_kissaten.duckdb` or `data/kissaten.duckdb` with a writable config unless `KISSATEN_ALLOW_PRODUCTION_DB=1` is set. The `kissaten refresh` CLI auto-sets this override.

### Tables
| Table | Purpose |
|---|---|
| `coffee_beans` | Main bean data (name, roaster, origin, process, price, etc.) |
| `origins` | Geographical hierarchy (country, region, farm, coordinates) |
| `roasters` | Roaster information and metadata |
| `country_codes` | ISO country code reference |
| `roaster_location_codes` | Roaster location → region code mapping |
| `tasting_notes_categories` | Three-tier tasting note classification |
| `processed_files` | Checksums for incremental loading (avoids re-processing unchanged JSON) |
| `currency_rates` | FX rates for price normalization |
| `price_options` | Individual bag size/price variants per bean (weight, price, currency, price_per_kg, price_per_kg_usd) |
| `varietal_mappings` | Raw → canonical varietal name mappings |
| `coffee_varietals` | Canonical varietal reference data |

### Full-Text Search
DuckDB FTS indexes on bean names, descriptions, tasting notes, and other text fields. The search endpoint combines FTS with relevance scoring.

### Incremental Loading
- Checksum-based diffing via `processed_files` table
- Only new/changed JSON files are loaded into DuckDB
- `kissaten refresh --incremental` triggers this after scraping

### UDFs
Custom DuckDB UDFs for name normalization (slugify, case-insensitive matching).

## Pydantic Schemas (`src/kissaten/schemas/`)

### Model Hierarchy
```
Bean (base)
  └── CoffeeBean (full model, scraped data)
        └── APICoffeeBean (API response with computed fields)
              ├── APISearchResult (search result with relevance score)
              └── APIRecommendation (recommendation with reasoning)

Roaster / RoasterConfig
SearchQuery (structured search request)
PaginationInfo
APIResponse[T] (generic response envelope with data + metadata + pagination)
```

### Key Models
- **`CoffeeBean`** (`schemas/coffee_bean.py`, ~25K): The core model. See [data/data-model.md](../data/data-model.md) for full field documentation.
- **`Roaster`** (`schemas/roaster_models.py`): Roaster info including name, website, location, scraping config. `RoasterDetailResponse` includes a multi-dimensional `UniquenessReport` that identifies where a roaster most over-indexes vs the global average across four dimensions — flavour (tasting-note primary category), origin (country), process (processing-method category slug), and varietal (varietal family slug). The report has a `top` insight (single strongest standout) plus `by_dimension` per-dimension winners, each with `display_label`, `this_roaster_pct`, `global_pct`, `lift`, `percentile`, `sample_size`, and an optional `link` to the relevant exploration route.
- **`SearchQuery`** (`schemas/search.py`): Structured search with filters, sorting, pagination.
- **`APIResponse`** (`schemas/api_models.py`): Generic `APIResponse[T]` wrapper used across all endpoints.
- **`geography_models.py`**: Country, region, farm models with ISO codes and coordinates.
- **`ai_search.py`**: `AISearchResponse`, `SearchParameters`, `SearchContext` for AI search.

## Protobuf (`src/kissaten/api/proto/`)
- `bean.proto` — Protobuf definition for BeanConqueror share links
- `bean_pb2.py` — Generated Python protobuf module
- Used by `beanconqueror_share.py` to encode bean data into share URLs
