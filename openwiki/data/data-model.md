---
type: "Reference"
title: "Data Model & Data Files"
description: "CoffeeBean Pydantic schema, DuckDB tables, JSON data files, Parquet exports, and the taste lexicon."
---

# Data Model & Data Files

## CoffeeBean Schema

The core data model is defined in `src/kissaten/schemas/coffee_bean.py`. It's a Pydantic v2 model serialized to JSON via `model_dump_json()`.

### Required Fields
- `name` — Bean name
- `roaster` — Roaster name
- `url` — Product page URL

### Optional Fields

**Identity & Media**
- `image_url` — Product image URL
- `description` — Product description (max 5000 chars)

**Origin** (array of origin objects)
- `country` — 2-letter ISO country code
- `region` — State/department/province
- `producer` — Producer name
- `farm` — Farm name
- `elevation_min` / `elevation_max` — Meters (0–3000m)
- `latitude` / `longitude` — GPS coordinates
- `process` — Processing method
- `variety` — Coffee varietal(s)
- `harvest_date` — Harvest date string
- `fob_price`, `farm_gate_price`, `price_paid_to_producer` — Cost transparency
- `price_currency` — Price currency code
- `importer_name` — Importer name

**Product**
- `is_single_origin` — Boolean
- `roast_level` — Enum: Extra-Light, Light, Light-Medium, Medium, Medium-Dark, Dark
- `roast_profile` — Enum: Espresso, Filter, Omni, Both
- `price_options` — Array of `{weight, price}` pairs
- `currency` — Price currency
- `is_decaf` — Boolean
- `cupping_score` — Float (70–100)

**Tasting**
- `tasting_notes` — Array of normalized strings

**Metadata**
- `in_stock` — Boolean
- `scraped_at` — ISO 8601 UTC timestamp
- `scraper_version` — Scraper version string
- `raw_data` — Original scraped HTML/data

See `BEAN_DATA_FORMAT.md` for the complete specification including diffjson format and bean UID generation.

For detailed documentation on all name mapping files (processing methods, varietals, tasting notes, farms, regions) and the AI categorizers that produce them, see [Name Mappings & Canonical Reference Data](name-mappings.md).

## DuckDB Tables

Managed by `src/kissaten/api/db.py`. The database file is at `data/kissaten.duckdb` (read-only, served by API) or `data/rw_kissaten.duckdb` (read-write, used by CLI refresh).

| Table | Purpose |
|---|---|
| `coffee_beans` | Main bean data with all fields above |
| `origins` | Geographical hierarchy (country, region, farm, coordinates, ISO codes) |
| `roasters` | Roaster metadata (name, website, location) |
| `country_codes` | ISO 3166 country code reference (`countrycodes.csv`) |
| `roaster_location_codes` | Roaster location → macro-region mapping |
| `tasting_notes_categories` | Three-tier tasting note classification |
| `processed_files` | File checksums for incremental loading |
| `currency_rates` | FX rates for price normalization to USD |
| `varietal_mappings` | Raw → canonical varietal name mappings |
| `coffee_varietals` | Canonical varietal reference data |

Full-text search (FTS) indexes are built on key text fields.

## Static Data Files (`src/kissaten/database/`)

### Mapping Files
| File                               | Size | Purpose                                          |
| ---------------------------------- | ---- | ------------------------------------------------ |
| `processing_methods_mappings.json` | 159K | Raw → canonical processing method names          |
| `varietal_mappings.json`           | 271K | Raw → canonical varietal names                   |
| `farm_mappings.json`               | 89K  | Farm name canonicalization (from dedup pipeline) |
| `coffee_varietals.json`            | 30K  | Reference list of canonical varietal names       |

### Lexicon & Categories
| File | Size | Purpose |
|---|---|---|
| `taste_lexicon.json` | 6K | Three-tier flavor taxonomy (primary/secondary/tertiary with flavor lists) |
| `tasting_notes_categorized.csv` | 190K | All tasting notes with assigned categories |
| `wikidata_flavour_images.json` | 444K | Flavour images from Wikidata (for UI display) |

### Geographic Reference
| File | Purpose |
|---|---|
| `countrycodes.csv` | Full ISO 3166 country code reference (name, alpha-2, alpha-3, region, sub-region) |
| `roaster_location_codes.csv` | Roaster location → region code (includes pseudo-codes for continents: XA=Asia, XF=Africa, XE=Europe) |
| `region_mappings/*.json` | ~50 per-country JSON files mapping raw region names to canonical administrative regions with ISO codes, coordinates, bounds, and confidence scores |

### Region Mapping Format
Each `region_mappings/<COUNTRY_CODE>.json` entry contains:
- `canonical_state` — Canonical region name
- `confidence` — 0–1 confidence score
- `reasoning` — AI reasoning for the selection
- `iso_3166_1_alpha_2`, `iso_3166_1_alpha_3` — Country codes
- `iso_3166_2` — Subdivision code
- `_category`, `_type` — Administrative classification
- `continent`, `country`, `state`, `state_code`
- `bounds` — NE/SW lat/lng bounding box
- `geometry` — lat/lng center point

## Data Pipeline

```
Scrapers → JSON files (data/roasters/) → DuckDB (incremental load via checksums)
                                              ↓
                                        FTS indexes
                                              ↓
                                        API endpoints
                                              ↓
                                        Frontend
```

### Incremental Loading
- `processed_files` table tracks content hashes of ingested JSON files
- `kissaten refresh --incremental` loads only new/changed files
- Smaller, frequent refreshes keep search results ~1 hour stale max

### `coffee_beans.filename` — absolute-path gotcha
`coffee_beans.filename` stores the **absolute path as written by the machine that scraped it**
(e.g. `/home/<user1>/kissaten/data/roasters/...`), so the prefix varies between environments and
is not meaningful locally. To resolve a local copy of a bean file, split on the stable marker
`kissaten/data/roasters/` and use the relative suffix under `data/roasters/`; a suffix that resolves
to no file simply means that scrape session is not present on this machine (files may have been
deleted or never synced). Never construct a checker by string-replacing the old machine's home prefix.

### Data Validation
- `kissaten validate-db` checks: volume drift vs last-known-good snapshot, required-field nulls, referential integrity, normalization invariants, 24h freshness, FTS index divergence
- Exits 1 on any failure, preventing promotion of rw DB to production

## Geocoding Service (`src/kissaten/services/geocoding.py`)

`OpenCageGeocoder` class:
- Uses OpenCage Geocoding API (`OPENCAGE_API_KEY`)
- File-based caching under `data/geocoding_cache/<COUNTRY_CODE>/<normalized_region>.json`
- Cache key normalization: NFKD unicode → ASCII → lowercase → strip non-alphanumeric → hyphens
- Works with `RegionSelector` AI agent: OpenCage returns candidates, Gemini picks the best
