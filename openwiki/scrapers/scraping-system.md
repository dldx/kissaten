# Scraping System

## Overview

Kissaten scrapes coffee bean data from 150+ roaster websites. Each roaster has its own scraper module in `src/kissaten/scrapers/`. The system uses a base class hierarchy, a decorator-based registry, and supports both simple HTML parsing (BeautifulSoup4) and JavaScript-heavy sites (Playwright).

## Base Classes

### `BaseScraper` (`src/kissaten/scrapers/base.py`)

A ~1,800-line abstract base class providing:

- **Dual fetching**: httpx for simple HTTP requests, Playwright for JS-rendered pages
- **Web Bot Auth**: When `BOT_PRIVATE_KEY_PEM`, `BOT_KEY_ID`, and `SIGNATURE_AGENT_URL` env vars are set, `get_signed_headers()` generates Ed25519-signed `Signature-Agent`, `Signature-Input`, and `Signature` headers for every outgoing request (both httpx and Playwright). Allows target servers to identify and verify the scraper as a legitimate bot. Requires the `cryptography` package.
- **Proxy credential parsing**: Playwright proxy URLs with embedded credentials (`scheme://user:pass@host:port`) are parsed so that username and password are passed separately to Playwright's launch options, which does not accept credentials in the proxy URL string.
- **AI extraction pipeline**: Integrates `CoffeeDataExtractor` (Gemini) for structured data extraction from HTML/screenshots
- **Page caching**: Saves fetched pages as tar archives for replay/debugging
- **Session tracking**: Timestamped scraping sessions under `data/roasters/<roaster>/<session>/`
- **Bean persistence**: Saves validated `CoffeeBean` objects as JSON
- **DiffJSON stock updates**: Tracks stock/field changes for already-known beans via `.diffjson` files
- **Error handling**: Retries, rate limiting, structured logging via Logfire

Subclasses must implement:
- `get_store_urls()` — return the list of roaster store/product URLs
- `_extract_product_urls_from_store()` — extract individual product page URLs from a store page

#### Session Stats and Failure Detection

The `scrape()` method tracks three session counters used by the CLI to determine success vs failure:

- `beans_found` — total product URLs discovered on the website (set to `len(all_product_urls)`)
- `beans_processed` — number of new beans actually scraped via AI extraction (may be 0 when all products are already known and only diffjson stock updates were created)
- `beans_found_in_stock` — count of existing products confirmed in stock via diffjson

The CLI (`run-all-scrapers`) marks a scraper as **failed** when `beans_found == 0`. A scraper that found products but only needed stock updates (no new beans to extract) is **not** a failure — `beans_found` reflects total products found, not just newly scraped ones. Scrapers that override `scrape()` directly (e.g. `dak.py`, `naughty_dog.py`) must set `session.beans_found` to the total product count, not just the count of newly extracted beans, to avoid false failure reports.

### `ShopifyJsonScraper` (`src/kissaten/scrapers/shopify_base.py`)

A specialized base for Shopify-based roasters. Shopify stores expose product data via the `/products.json` API, making scraping more reliable than HTML parsing. ~60 of the 200 scrapers inherit from this.

## Scraper Registry (`src/kissaten/scrapers/registry.py`)

Uses a decorator pattern for auto-registration:

```python
@register_scraper
class CartwheelCoffeeScraper(BaseScraper):
    ...
```

The registry:
- Auto-discovers scrapers at import time via `@register_scraper`
- `src/kissaten/scrapers/__init__.py` imports all 150+ scraper modules, triggering registration
- Access via `get_registry()` singleton
- Each entry includes scraper name, class, status (available/buggy/disabled)

## Adding New Scrapers

See `ADDING_SCRAPERS.md` and `.opencode/skills/` for detailed guides. The process:

1. Create `src/kissaten/scrapers/<roaster_name>.py`
2. Inherit from `BaseScraper` (general) or `ShopifyJsonScraper` (Shopify stores)
3. Implement `get_store_urls()` and `_extract_product_urls_from_store()`
4. Add the `@register_scraper` decorator
5. Update `src/kissaten/scrapers/__init__.py` to import the new module
6. Add tests in `tests/unit/`

**Critical rule**: Never hardcode coffee bean values in scrapers. Extract all data from HTML/API responses so scrapers remain future-proof for new beans, origins, etc.

### Scraper Template

`src/kissaten/scrapers/template.py` provides a reference implementation showing all required methods and patterns.

### Skills

- `.opencode/skills/shopify-scraper/SKILL.md` — Guide for Shopify-based scrapers
- `.opencode/skills/non-shopify-scraper/SKILL.md` — Guide for custom/non-Shopify scrapers

## Data Output Format

Scraped data is saved under:
```
data/roasters/<roaster_name>/<session_date>/
├── <bean_uid>.json           # Full bean data (CoffeeBean.model_dump_json())
├── <bean_uid>.original.json   # Original-language version (optional, for translation)
├── <bean_uid>.png             # Product image screenshot (optional)
└── <product_slug>.diffjson   # Stock/field update diffs for known beans
```

- Session dates use ISO format: `2024-01-15T10-30-00`
- Bean UID: cleaned bean name + process suffix + timestamp (HHMMSS), truncated to 100 chars
- See `BEAN_DATA_FORMAT.md` for the complete data format specification

## Batch Scraping & Scheduling

The CLI `run-all-scrapers` command supports batch scraping:
- `--num-batches N` — Split scrapers into N chunks
- `--batch-index I` — Run chunk I (0-indexed)
- `--date YYYY-MM-DD` — Seed for deterministic shuffle (defaults to today UTC)
- After each batch: auto-runs `kissaten refresh --incremental` and `kissaten validate-db`

Default schedule: 16 hourly batches, 06:00–21:00 UTC. See [operations/operations.md](../operations/operations.md) for cron configuration.

## Deduplication Pipeline

`src/kissaten/dedup/` provides farm-name canonicalization:

1. **Normalize** (`normalizer.py`) — Clean and standardize farm names
2. **Match** (`matcher.py`) — Fuzzy match using rapidfuzz
3. **Cluster** (`clusterer.py`) — Union-Find clustering of matching names
4. **Review** (`tui.py`) — Interactive Textual TUI for reviewing proposed merges
5. **Export** (`storage.py`) — Write canonical mappings to `database/farm_mappings.json`

This ensures that "Finca La Esperanza" and "La Esperanza Farm" are recognized as the same producer.
