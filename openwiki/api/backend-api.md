---
type: "Reference"
title: "Backend API & Database"
description: "FastAPI endpoints, DuckDB layer, sub-routers, Pydantic schemas, and protobuf share-link generation for the Kissaten backend."
generated: { by: "openwiki/0.4.3", at: "2026-08-29T13:59:13.975Z" }
---

# Backend API & Database

## FastAPI Application (`src/kissaten/api/main.py`)

The main FastAPI app exposes 33+ endpoints and mounts 4 sub-routers. Endpoints are cached with `aiocache`'s `SimpleMemoryCache` (`@cached`) where marked. Key endpoint groups:

### Core Search & Browse
- `GET /api/v1/search` — Full-text search with faceted filtering (origin, roaster, process, varietal, price, roast level, availability, review/kit status). Supports **largest-bag (bulk) pricing** via the `price_options` table: `price_large_*` response fields, `sort_by=price_large`, and the `min_large_weight` filter (hard `lb_weight >= ?` on the `largest_bag` CTE). See [Largest-Bag Pricing](#largest-bag-pricing-price_options).
- `GET /api/v1/roasters` — All roasters with metadata (name, slug, website, location, email, active, counts) plus `location_codes`, `country_slug` and `region_slug` from the hierarchical location-code mapping, used for client-side geographic filtering
- `GET /api/v1/roasters/{roaster_slug}` — Roaster detail (beans, stats, origin/varietal breakdown, uniqueness report). Accepts `include_unreviewed` (admin) to reveal review-pending rows.
- `GET /api/v1/roasted-in/{slug}` — Location (country or region) exploration: statistics, top roasters, top cities/countries, top origins, top varietals
- `GET /api/v1/stats` — Database statistics and analytics

### Origin & Geography
- `GET /api/v1/origins` — Coffee origin countries with bean + roaster counts
- `GET /api/v1/origins/{country_code}` — Country detail with statistics and hierarchy
- `GET /api/v1/origins/{country_code}/regions` — Region list for a country
- `GET /api/v1/origins/{country_code}/{region_slug}` — Region detail (farms, roasters, tasting notes, varietals, processing methods, elevation range)
- `GET /api/v1/origins/{country_code}/{region_slug}/{farm_slug}` — Farm detail
- `GET /api/v1/search/origins` — Unified origin search (country / region / farm)
- `GET /api/v1/country-codes` — ISO 3166 country code reference

### Tasting & Flavours
- `GET /api/v1/tasting-note-categories` — Tasting note categories (three-tier hierarchy)
- `GET /api/v1/search/by-tasting-category` — Bean search by tasting category
- `GET /api/v1/tasting-notes/{note_text}/details` — Tasting-note detail
- `GET /api/v1/flavour-images` — Flavour images for the UI

### Recommendations
- `GET /api/v1/beans/{roaster_slug}/{bean_slug}/recommendations` — Bean recommendations based on attributes

### BeanConqueror Share
- `GET /api/v1/beans/{roaster_slug}/{bean_slug}/beanconquerer-link` — Generate a BeanConqueror app share link

### Roaster Uniqueness Report
The roaster detail endpoint (`GET /api/v1/roasters/{roaster_slug}`) computes a multi-dimensional [roaster uniqueness report](roaster-uniqueness.md) that identifies where a roaster most over-indexes vs the global average across flavour, origin, process, and varietal dimensions. See [roaster-uniqueness.md](roaster-uniqueness.md) for the full algorithm, threshold gates, SQL queries, and Pydantic models.

### Sitemaps
- XML sitemap endpoints for SEO (origins, processes, varietals, static pages)

### Roaster-Location Exploration
- `GET /api/v1/roaster-locations` — List locations with codes (for client-side filtering)
- `GET /api/v1/roasted-in/{slug}` — Detailed view of a country or region: resolves the slug against `roaster_location_codes`, matches roasters hierarchically via `get_hierarchical_location_codes()` (country codes, plus continental pseudo-codes like `XE` and the `EU` special case for EU members), and returns `LocationDetailResponse` with statistics (available/total beans, roaster count, city count for countries / country count for regions), top roasters with per-city location, top cities (countries) or top countries (regions), top bean-source origins, top varietals, and a per-country breakdown for regions. Cached with `SimpleMemoryCache`.

## Sub-Routers

### AI Search (`src/kissaten/api/ai_search.py`)
9 endpoints under `/v1/ai/*`:
- Image-based bean extraction (Gemini analyses product screenshots)
- Natural language search (translates queries to structured search params)
- Search result caching with feedback (thumbs up/down)
- Rate-limited

The AI search agent uses keyword-based context filtering to send only relevant database entries to the model (see [ai/ai-pipeline.md](../ai/ai-pipeline.md) § Search Architecture v2).

### Brew Assistant (`src/kissaten/api/brew_assistant.py`)
- `POST /v1/brew-assistant/recipe` — Generates personalized pour-over/espresso recipes using PydanticAI + Gemini, considering bean attributes and user equipment

Request model (`BrewRecipeRequest`) in detail:
- `bean_name`, `process`, `roast_level`, `roast_profile`, `description`, `tasting_notes`, `personal_notes`, `parameters` (dose, brewer, grinder, water ratio)
- `additional_guidance` — the user's **preferred technique** (pour structure, time, temperature, grind tendency). The prompt treats it as advisory: the requested dose/brewer/grinder stay fixed, and the guidance is *adapted* to them — scales pour sizes/ratios when written for a different dose, translates grind settings onto the user's actual grinder, and explicitly states in the introduction if any guided element is dropped (no silent ignores).
- `previous_brewing_notes` — since Aug 2026 a structured `PreviousBrewingNotes` with **two buckets**:
  - `for_this_bean` — past notes for the *same* bean (name + roaster); highest-signal personal context; the `concise_brewing_summary` mimics its phrasing when present.
  - `for_other_beans` — generic past style; soft context only, never allowed to override the current bean's process/origin/roast signals.
  - The prompt includes a priority ladder: `parameters` + `personal_notes` (fixed) → `additional_guidance` (adapted) → `for_this_bean` (style mimicry) → `for_other_beans` (soft) → extraction-theory defaults (only where nothing above applies).

### FX / Currency (`src/kissaten/api/fx.py`)
4 endpoints for currency conversion:
- List supported currencies
- Convert amounts
- Update/refresh rates (backed by `currency_rates` DuckDB table)
- 10-minute response caching

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
| `coffee_beans` | Main bean data (name, roaster, origin, process, price, etc.) — since Aug 2026 also `is_tasting_kit` and `requires_review` boolean flags (both default `false`) |
| `origins` | Geographical hierarchy (country, region, farm, coordinates) |
| `roasters` | Roaster information and metadata |
| `country_codes` | ISO country code reference |
| `roaster_location_codes` | Roaster location → region code mapping (used by `roasted-in` and hierarchical location codes) |
| `tasting_notes_categories` | Three-tier tasting note classification |
| `processed_files` | Checksums for incremental loading (avoids re-processing unchanged JSON) |
| `currency_rates` | FX rates for price normalization |
| `price_options` | Individual bag size/price variants per bean (weight, price, currency, price_per_kg, price_per_kg_usd) — drives largest-bag (bulk) pricing |
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
- **`CoffeeBean`** (`schemas/coffee_bean.py`, ~25K): The core model. Since Aug 2026 it carries two review-related flags: `is_tasting_kit` (curated multi-coffee kit/sampler/set — persistent category flag) and `requires_review` (hidden from public search pending human review), mirrored on `CoffeeBeanDiffUpdate` and `CoffeeBeanOptional` so diffjson updates can flip them. See [data/data-model.md](../data/data-model.md) for full field documentation.
- **`APISearchResult`** (`schemas/api_models.py`): Search result with relevance score plus `price_large_weight`, `price_large_price`, `price_large_price_per_kg_usd` (largest-bag pricing fields, renamed from the internal `lb_*` query columns).
- **`Roaster`** (`schemas/roaster_models.py`): Roaster info including name, website, location, scraping config. `RoasterDetailResponse` includes a multi-dimensional `UniquenessReport` that identifies where a roaster most over-indexes vs the global average across four dimensions — flavour (tasting-note primary category), origin (country), process (processing-method category slug), and varietal (varietal family slug). The report has a `top` insight (single strongest standout) plus `by_dimension` per-dimension winners, each with `display_label`, `this_roaster_pct`, `global_pct`, `lift`, `percentile`, `sample_size`, and an optional `link` to the relevant exploration route.
- **`LocationDetailResponse`** (`schemas/geography_models.py`): Response for `/v1/roasted-in/{slug}` — `location_type` (`country`|`region`), `statistics` (`LocationStatistics`), `top_roasters`, `top_cities`/`countries`, `top_origins`, `varietals`.
- **`SearchQuery`** (`schemas/search.py`): Structured search with filters, sorting, pagination.
- **`APIResponse`** (`schemas/api_models.py`): Generic `APIResponse[T]` wrapper used across all endpoints.
- **`ai_search.py`**: `AISearchResponse`, `SearchParameters`, `SearchContext` for AI search.

## Largest-Bag Pricing (`price_options`)

`/v1/search` and `/v1/search/by-paths` both join a `largest_bag` CTE (`DISTINCT ON (bean_id)` from `price_options` where `price_per_kg_usd IS NOT NULL`, ordered by `weight DESC, price DESC`) so every bean result carries the **largest available bag**:

- `price_large_weight` (g), `price_large_price` (converted to the requested currency), `price_large_price_per_kg_usd`
- `sort_by=price_large` sorts by `COALESCE(sb.lb_price_per_kg_usd, sb.price_usd / NULLIF(sb.weight, 0))` — a cheap per-kg proxy for "bulk value"
- `min_large_weight` is a **hard** filter (`cb.lb_weight >= ?`) applied in both the count and main queries, mirroring `in_stock`/`is_decaf`
- Currency conversion for the large-bag price goes through `_build_currency_select_sql`'s `lb_price_sql`: it uses the USD `price_per_kg_usd` as the base (falling back to raw `lb_price`) and is parameterized, never interpolated

The `price_options` table is rebuilt on every refresh from the bean JSON `price_options` arrays (`weight`, `price` × bean `currency`), with `price_per_kg = price / (weight/1000)`; `price_per_kg_usd` is populated during the USD-normalization pass. Child rows are deleted before their parent bean (foreign key `bean_id → coffee_beans.id`), and the table is dropped ahead of the parent in `init_database`'s ordered `DROP` list.

## Review-Flag & Kit Search Contract

`FilterParams` (and both search endpoints' query params) gained `is_tasting_kit`, `requires_review`, and `include_unreviewed` (default `false`). Their behaviour in `build_coffee_bean_filters`:

| Param | Semantics |
|---|---|
| `is_tasting_kit` | **Hard filter** like `is_decaf` — `cb.is_tasting_kit = ?`. Powers the public "Sampling kits" search filter. |
| `requires_review` | **Hard filter when set** — `cb.requires_review = ?`. Querying review status is an admin action (the admin queue uses `requires_review=true`), and it **suppresses** the default hide clause. |
| `include_unreviewed=true` | Reveals hidden rows for admin views: the default `WHERE requires_review = false` clause is skipped. |

The default gate is the module-level constant `REVIEW_HIDDEN_SQL = "cb.requires_review = false"` (plus an `_SB` variant for the outer `sb`-aliased queries), applied in every public list path:

- `/v1/search` and `/v1/search/by-paths` (via `build_coffee_bean_filters`)
- `/v1/roasters/{roaster_slug}` bean list — `include_unreviewed` query param defaults to `false`
- `/v1/beans/{roaster_slug}/{bean_slug}` selects `requires_review` but does **not** hide the row — a reviewer must be able to open a pending product
- `/v1/stats` is untouched: review-flagged rows still count

Full lifecycle, flags, admin review UI and the `kissaten apply-review-decisions` CLI live in [operations/tasting-kit-review-pipeline.md](../operations/tasting-kit-review-pipeline.md).

## Protobuf (`src/kissaten/api/proto/`)
- `bean.proto` — Protobuf definition for BeanConqueror share links
- `bean_pb2.py` — Generated Python protobuf module
- Used by `beanconqueror_share.py` to encode bean data into share URLs
