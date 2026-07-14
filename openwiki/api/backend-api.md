# Backend API & Database

## FastAPI Application (`src/kissaten/api/main.py`)

The main FastAPI app exposes 33+ endpoints and mounts 4 sub-routers. Key endpoint groups:

### Core Search & Browse
- `GET /api/v1/search` — Full-text search with faceted filtering (origin, roaster, process, varietal, price, roast level, availability)
- `GET /api/v1/beans/{id}` — Individual bean detail
- `GET /api/v1/roasters` — List all roasters with metadata
- `GET /api/v1/roasters/{name}/beans` — Beans from a specific roaster
- `GET /api/v1/countries` — Coffee origin countries
- `GET /api/v1/stats` — Database statistics and analytics

### Origin & Geography
- `GET /api/v1/origins` — Coffee origins with hierarchy (country → region → farm)
- Origin statistics, region mappings, geographical data

### Tasting & Flavours
- `GET /api/v1/tasting-notes/categories` — Tasting note categories (three-tier hierarchy)
- Flavour profile endpoints

### Recommendations
- `GET /api/v1/recommend` — Bean recommendations based on attributes

### BeanConqueror Share
- `GET /api/v1/beans/{id}/beanconqueror` — Generate a BeanConqueror app share link

### Sitemaps
- XML sitemap endpoints for SEO (origins, processes, varietals, static pages)

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
- **`Roaster`** (`schemas/roaster_models.py`): Roaster info including name, website, location, scraping config.
- **`SearchQuery`** (`schemas/search.py`): Structured search with filters, sorting, pagination.
- **`APIResponse`** (`schemas/api_models.py`): Generic `APIResponse[T]` wrapper used across all endpoints.
- **`geography_models.py`**: Country, region, farm models with ISO codes and coordinates.
- **`ai_search.py`**: `AISearchResponse`, `SearchParameters`, `SearchContext` for AI search.

## Protobuf (`src/kissaten/api/proto/`)
- `bean.proto` — Protobuf definition for BeanConqueror share links
- `bean_pb2.py` — Generated Python protobuf module
- Used by `beanconqueror_share.py` to encode bean data into share URLs
