---
type: "Reference"
title: "Data Model & Data Files"
description: "CoffeeBean Pydantic schema, DuckDB tables, JSON data files, and the taste lexicon, with cross-links from each field group to its Coffee Domain Concept page."
tags: [data-model, pydantic, duckdb, schema, coffee-bean, taste-lexicon, kissaten]
verified:
  - by: openwiki/0.4.3
    at: 2026-08-29T13:59:13.975Z
sources:
  - id: openwiki-source-1c4eb588008fec479eca4e07
    resource: repo://BEAN_DATA_FORMAT.md
  - id: openwiki-source-b6db435ba1198be65f340e6b
    resource: repo://src/kissaten/api/db.py
  - id: openwiki-source-9735fcc3e14d5d9974206d6d
    resource: repo://src/kissaten/api/main.py
  - id: openwiki-source-518e35e959773aac7710e8ac
    resource: repo://src/kissaten/cli/main.py
  - id: openwiki-source-641e33b1b97d9d6c94b2f983
    resource: repo://src/kissaten/database/coffee_varietals.json
  - id: openwiki-source-a9c5ae46b99ccf7ee016bc03
    resource: repo://src/kissaten/database/countrycodes.csv
  - id: openwiki-source-6e06f9a789b1789685e31c25
    resource: repo://src/kissaten/database/farm_mappings.json
  - id: openwiki-source-25e752e5a32e4e26ca7b6c98
    resource: repo://src/kissaten/database/processing_methods_mappings.json
  - id: openwiki-source-030b07af7e3a048efec233fd
    resource: repo://src/kissaten/database/region_mappings/ET.json
  - id: openwiki-source-4fffdd5aff518d52fa9f58b5
    resource: repo://src/kissaten/database/roaster_location_codes.csv
  - id: openwiki-source-aa7b0286107825e00b412cf8
    resource: repo://src/kissaten/database/taste_lexicon.json
  - id: openwiki-source-ff88345ee75129d53d705bdf
    resource: repo://src/kissaten/database/tasting_notes_categorized.csv
  - id: openwiki-source-d3d8700263a5c9e98693f9cd
    resource: repo://src/kissaten/database/varietal_mappings.json
  - id: openwiki-source-c8d02ad8153c738314dc044f
    resource: repo://src/kissaten/database/wikidata_flavour_images.json
  - id: openwiki-source-a91bd1e17d487f691b479d46
    resource: repo://src/kissaten/schemas/coffee_bean.py
  - id: openwiki-source-d09264b76831d20864b449c9
    resource: repo://src/kissaten/services/geocoding.py
generated: { by: "openwiki/0.4.3", at: "2026-08-29T13:59:13.975Z" }
---

# Data Model & Data Files

Kissaten's data model has three layers: a **Pydantic v2 schema** (`CoffeeBean` and friends) that
validates scraped data, a set of **JSON data files** on disk under `data/roasters/` and
`src/kissaten/database/`, and a **DuckDB** analytical database built from those JSON files that
serves the API. This page documents the schema fields, the DuckDB tables and full-text search
indexes, the static reference files, and the load/validate pipeline that connects them. Each field
group below links out to the Coffee Domain Concept page that explains what the values *mean* in
specialty-coffee terms.

## CoffeeBean Schema

The core data model is defined in `src/kissaten/schemas/coffee_bean.py`. It is a Pydantic v2 model
serialised to JSON via `model_dump_json()`. The package defines several cooperating models:

- `CoffeeBean` — the full validated record written by scrapers to `<bean_uid>.json`.
- `Bean` — a single origin entry inside the `origins` array (one for single-origin, several for
  blends).
- `PriceOption` — one `{weight, price}` bag variant.
- `CoffeeBeanDiffUpdate` — a partial update applied via `.diffjson` files; only `url` is required and
  the model serialises with `exclude_none=True`.
- `CoffeeBeanOptional` — a lenient mirror of `CoffeeBean` in which every field is optional, used to
  extract images or other incomplete sources without being rejected for missing required fields.

### Required Fields
- `name` — Bean name (1–200 chars)
- `roaster` — Roaster name (1–100 chars)
- `url` — Product page URL (Pydantic `HttpUrl`)
- `origins` — Non-empty list of `Bean` origin objects
- `price_options` — List of `PriceOption` bag variants

### Optional Fields

**Identity & Media**
- `image_url` — Product image URL
- `description` — Product description (max 8000 chars on `CoffeeBean`; 5000 in the diff-update model)

**Origin** (array of `Bean` objects) — see [Origin Geography](../concepts/origin-geography.md)
- `country` — 2-letter ISO country code, upper-cased by a field validator
- `region` — State/department/province, title-cased
- `producer` — Producer name
- `farm` — Farm name, title-cased
- `elevation_min` / `elevation_max` — Metres above sea level (`0`–`3000`, default `0`); a
  model validator swaps them if `max < min`
- `latitude` / `longitude` — GPS coordinates (lat `±90`, lng `±180`); "do not guess"
- `process` — Processing method → [Processing Methods](../concepts/processing-methods.md)
- `variety` — Coffee varietal(s) → [Varietals](../concepts/varietals.md)
- `harvest_date` — ISO 8601 datetime; must be after 2020 and not in the future
- `fob_price`, `farm_gate_price`, `price_paid_to_producer` — Cost transparency (USD per kg, must be
  between $0.50 and $300) → [Price Transparency](../concepts/price-transparency.md)
- `price_currency` — Price currency code (3 chars)
- `importer_name` — Importer / trading company name

**Product**
- `is_single_origin` — Boolean (default `true`)
- `roast_level` — Enum → [Roast Levels & Roast Profiles](../concepts/roast-levels-profiles.md).
  The `RoastLevel` enum members are `Extra-Light`, `Light`, `Medium-Light`, `Medium`,
  `Medium-Dark`, `Dark`.
- `roast_profile` — Literal enum → [Roast Levels & Roast Profiles](../concepts/roast-levels-profiles.md):
  `Espresso`, `Filter`, `Omni`, `Both`
- `price` / `weight` / `currency` — Default bag price, weight (g), and 3-letter currency
  (default `GBP`). If `price`/`weight` are unset, a model validator picks the `price_options` entry
  nearest to 200 g.
- `price_options` — Array of `PriceOption` `{weight, price}` pairs (drives the `price_options`
  DuckDB table and largest-bag pricing). Duplicates by `(weight, price)` are removed by a field
  validator. A model validator enforces a USD-per-gram sanity range against `fx` exchange rates.
- `is_decaf` — Boolean (default `false`) → [Decaffeination](../concepts/decaffeination.md)
- `cupping_score` — Float (`70`–`100`) → [Cupping Scores](../concepts/cupping-scores.md)
- `is_tasting_kit` — Boolean (default `false`): curated multi-coffee tasting kit/sampler/set.
  Persistent category flag that survives stock-update diffs; powers the "Sampling kits" search
  filter.
- `requires_review` — Boolean (default `false`): product is hidden from public search until a human
  approves it. Set to `true` at scrape time for brand-new kits; approved products flip to `false`
  via a review diffjson (see `apply-review-decisions`).

**Tasting**
- `tasting_notes` — Array of normalised strings (title-cased, deduplicated, order-preserving). A
  single long note is split via the `TastingNoteSplitter` AI agent when `GOOGLE_API_KEY` is set →
  [Tasting Note Taxonomy](../concepts/tasting-note-taxonomy.md)

**Metadata**
- `in_stock` — Boolean (treat as `true` if stock is not mentioned as out)
- `scraped_at` — ISO 8601 UTC timestamp (defaults to now-UTC)
- `scraper_version` — Scraper version string (default `"1.0"`)
- `raw_data` — Original scraped HTML/data

> See `BEAN_DATA_FORMAT.md` for the complete on-disk specification, including the diffjson format
> and bean-UID generation. For the mapping files that turn raw strings into canonical processing
> methods, varietals, tasting notes, farms, and regions, see
> [Name Mappings & Canonical Reference Data](name-mappings.md).

## DuckDB Tables

Managed by `src/kissaten/api/db.py`. The database file is at `data/kissaten.duckdb` (read-only,
served by the API) or `data/rw_kissaten.duckdb` (read-write, used by CLI refresh). `KISSATEN_USE_RW_DB=1`
selects the read-write path; otherwise the module opens the production DB read-only and hardens it
with `enable_external_access = false`. A production-DB safety guard refuses to open a protected DB
with a writable config unless `KISSATEN_ALLOW_PRODUCTION_DB=1` is set.

| Table | Purpose |
|---|---|
| `coffee_beans` | Main bean data with all fields above — including `price_usd`, `date_added`, `clean_url_slug`, `bean_url_path`, `filename`, `name_unaccented`, and the `is_tasting_kit` / `requires_review` flags |
| `origins` | Geographical hierarchy keyed to `coffee_beans.id` (`bean_id` FK): country, region, `region_normalized`, producer, farm, `farm_normalized`, coordinates, `process`, `process_common_name`, `variety`, `variety_canonical[]`, `harvest_date`, plus derived canonical/slug columns (`state_canonical`, `farm_canonical`, `process_slug`, `process_common_slug`, `variety_canonical_slugs[]`, `*_unaccented`, `state_canonical_slug`) |
| `price_options` | Per-bean bag variants: `weight`, `price`, `currency` (from the bean), `price_per_kg`, `price_per_kg_usd`. Rebuilt on every refresh; feeds the `largest_bag` CTE behind `price_large_*` API fields and `price_large` sorting. |
| `roasters` | Roaster metadata (name, slug, website, location, email, active, last_scraped, total_beans_scraped, description) |
| `country_codes` | ISO 3166 country code reference (`countrycodes.csv`) |
| `roaster_location_codes` | Roaster location → macro-region mapping (incl. continent pseudo-codes: XA=Asia, XF=Africa, XE=Europe) |
| `tasting_notes_categories` | Three-tier tasting note classification |
| `processed_files` | File checksums for incremental loading (`file_path`, `checksum`, `file_type`, `processed_at`) |
| `currency_rates` | FX rates for price normalization to USD (`base_currency`, `target_currency`, `rate`, `fetched_at`) |
| `varietal_mappings` | Raw → canonical varietal name mappings (`original_name`, `canonical_names[]`, `confidence`, `is_compound`, `separator`) |
| `coffee_varietals` | Canonical varietal reference data (`name`, `description`, `link`, `species`) |

Two convenience views are created during `init_database()`:

- `coffee_beans_with_origin` — `coffee_beans` LEFT JOINed to the first origin per bean (DISTINCT ON
  `bean_id` ORDER BY `bean_id, id`) and to `country_codes` for the full country name.
- `roasters_with_location` — `roasters` LEFT JOINed to `roaster_location_codes` for the
  `roaster_country_code`.

### Full-Text Search (FTS)

`ensure_fts_index()` rebuilds a `coffee_beans_fts_source` table that joins `coffee_beans` with
aggregated origin text (all countries, regions, producers, farms, processes, varieties, plus the
roaster location) and the `tasting_notes` array, then issues `PRAGMA create_fts_index` over the
columns `name`, `roaster`, `roaster_country`, `tasting_notes`, `countries`, `regions`,
`producers`, `farms`, `processes`, and `varieties`. The FTS extension is loaded in read-only API
mode (a process-local `LOAD fts`, not a DB write); `INSTALL fts` is attempted as a fallback and
failures are logged.

Indexes created for query speed include `idx_origins_process_slug`,
`idx_origins_process_common_slug`, `idx_origins_process_common_name`,
`idx_origins_state_canonical_slug`, `idx_origins_farm_unaccented`, `idx_beans_name_unaccented`,
`idx_price_options_bean_id`, and `idx_price_options_price_per_kg_usd`.

### `price_options` → `price_large` flow

On refresh, `price_options` rows are inserted by UNNESTing the `price_options` array of each
loaded bean, computing `price_per_kg = price / (weight / 1000)`. After currency rates are loaded,
`price_per_kg_usd` is back-filled by dividing by the latest USD→`currency` rate. At query time the
API builds a `largest_bag` CTE (`DISTINCT ON (bean_id)` ordered by `weight DESC, price DESC` from
`price_options` where `price_per_kg_usd` is not null); its `lb_*` columns are exposed as
`price_large_weight`, `price_large_price`, and `price_large_price_per_kg_usd`, and the
`price_large` sort key orders beans by the cheapest-per-kg largest bag.

## Static Data Files (`src/kissaten/database/`)

### Mapping Files
| File                               | Size  | Purpose                                          |
| ---------------------------------- | ----- | ------------------------------------------------ |
| `processing_methods_mappings.json` | ~245K | Raw → canonical processing method names          |
| `varietal_mappings.json`           | ~261K | Raw → canonical varietal names                   |
| `farm_mappings.json`               | ~89K  | Farm name canonicalization (from dedup pipeline) |
| `coffee_varietals.json`            | ~30K  | Reference list of canonical varietal names       |

### Lexicon & Categories
| File | Size | Purpose |
|---|---|---|
| `taste_lexicon.json` | ~6K | Three-tier flavour taxonomy (primary/secondary/tertiary with flavour lists) |
| `tasting_notes_categorized.csv` | ~207K | All tasting notes with assigned categories |
| `wikidata_flavour_images.json` | ~444K | Flavour images from Wikidata (for UI display) |

### Geographic Reference
| File | Purpose |
|---|---|
| `countrycodes.csv` | Full ISO 3166 country code reference (name, alpha-2, alpha-3, region, sub-region) |
| `roaster_location_codes.csv` | Roaster location → region code (includes pseudo-codes for continents: XA=Asia, XF=Africa, XE=Europe) |
| `region_mappings/*.json` | ~50 per-country JSON files mapping raw region names to canonical administrative regions with ISO codes, coordinates, bounds, and confidence scores |

### Region Mapping Format

- `canonical_state` — Canonical region name
- `confidence` — 0–1 confidence score
- `reasoning` — AI reasoning for the selection
- `iso_3166_1_alpha_2`, `iso_3166_1_alpha_3` — Country codes
- `iso_3166_2` — Subdivision code
- `_category`, `_type` — Administrative classification
- `continent`, `country`, `state`, `state_code`
- `bounds` — NE/SW lat/lng bounding box
- `geometry` — lat/lng centre point

## Data Pipeline

<!-- openwiki: mermaid parse failed and this diagram was converted to a text fence so it does not break rendering. Fix the diagram source and restore the mermaid fence. Parser error: Heuristic: a semicolon inside a label breaks rendering; rephrase the label. -->
```text
flowchart TD
    SC["Scrapers"] --> JSON["JSON files<br/>data/roasters/&lt;roaster&gt;/&lt;session&gt;/"]
    JSON -->|"incremental load via checksums"| DB["DuckDB<br/>coffee_beans / origins / price_options"]
    DB -->|"ensure_fts_index"| FTS["FTS index<br/>coffee_beans_fts_source"]
    DB -->|"views"| API["API endpoints"]
    FTS --> API
    API --> FE["Frontend"]
```

The diagram shows the flow from scrapers to the frontend: scrapers write per-bean JSON under
`data/roasters/`, the refresh loader ingests them into DuckDB, the FTS index and views are rebuilt,
and the API serves both to the frontend.

### Incremental Loading
- `processed_files` table tracks content hashes of ingested JSON and diffjson files
- `kissaten refresh --incremental` loads only new/changed files; `check_for_changes` verifies
  checksums to detect changes
- Smaller, frequent refreshes keep search results ~1 hour stale max

### `coffee_beans.filename` — absolute-path gotcha
`coffee_beans.filename` stores the **absolute path as written by the machine that scraped it**
(e.g. `/home/<user1>/kissaten/data/roasters/...`), so the prefix varies between environments and
is not meaningful locally. To resolve a local copy of a bean file, split on the stable marker
`kissaten/data/roasters/` and use the relative suffix under `data/roasters/`; a suffix that resolves
to no file simply means that scrape session is not present on this machine (files may have been
deleted or never synced). Never construct a checker by string-replacing the old machine's home prefix.

### Data Validation
`kissaten validate-db [--db-path <path>] [--update-snapshot]` runs eight check categories against a
DuckDB file (default `data/rw_kissaten.duckdb`), each wrapped in its own logfire span:

- **A. Volume drift** — table row counts vs. last-known-good snapshot (±2 %)
- **B. Required fields** — `name`, `roaster`, `url`, `scraped_at`, `in_stock` non-null
- **C. Referential integrity** — beans↔roasters and beans↔origins links intact
- **D. Normalization** — `price`→`price_usd`, `currency_rates` coverage
- **E. Freshness** — at least one bean scraped in the last 24 h
- **F. FTS index** — source within 200 rows of beans, index artifacts
  (`fts_main_coffee_beans_fts_source.docs` / `.terms`) populated, and a `match_bm25` probe returns
  at least one hit
- **G. In-stock drift** — global/per-roaster in-stock counts vs snapshot (mass flips blocked)
- **H. Batch health** — last scraping batch (`data/last_batch_results.json`) did not mostly fail
  (≥50 % scraper failures blocks promotion)

It exits 1 on any failure, preventing promotion of the rw DB to production. With `--update-snapshot`
the snapshot is rewritten only if all checks pass.

## Geocoding Service (`src/kissaten/services/geocoding.py`)

`OpenCageGeocoder` class:
- Uses the OpenCage Geocoding API (key from `OPENCAGE_API_KEY`)
- File-based caching under `data/geocoding_cache/<COUNTRY_CODE>/<normalized_region>.json`
- Cache key normalization: NFKD unicode → ASCII → lowercase → strip non-alphanumeric → hyphens
- Works with the `RegionSelector` AI agent: OpenCage returns candidates, Gemini picks the best
