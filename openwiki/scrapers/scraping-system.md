---
type: "Reference"
title: "Scraping System"
description: "BaseScraper and ShopifyJsonScraper class hierarchy, decorator-based scraper registry, session tracking, deduplication pipeline, batch scraping, and how to add new scrapers."
---

# Scraping System

## Overview

Kissaten scrapes coffee bean data from 200+ roaster websites. Each roaster has its own scraper module in `src/kissaten/scrapers/`. The system uses a base class hierarchy, a decorator-based registry, and supports both simple HTML parsing (BeautifulSoup4) and JavaScript-heavy sites (Playwright).

## Base Classes

### `BaseScraper` (`src/kissaten/scrapers/base.py`)

A ~1,800-line abstract base class providing:

- **Dual fetching**: a thin [curl_cffi](https://github.com/yifeikong/curl_cffi)-backed shim (`src/kissaten/scrapers/_curl_http.py`, exposed as `from . import _curl_http as httpx`) for simple HTTP requests, Playwright for JS-rendered pages. The shim re-exports the httpx-shaped names the scrapers use (`AsyncClient`, `Auth`, `HTTPStatusError`, `RequestError`) so the call sites stay unchanged; under the hood it wraps `curl_cffi.requests.AsyncSession` whose libcurl TLS/HTTP2 stack passes the Shopify fingerprint-based throttle that bare `httpx` was being 429'd by. See [curl_cffi Swap — 2026-08](../operations/curl-cffi-swap-2026-08.md) for the full incident report and probe results.
- **Web Bot Auth**: When `BOT_PRIVATE_KEY_PEM`, `BOT_KEY_ID`, and `SIGNATURE_AGENT_URL` env vars are set, `get_signed_headers()` generates Ed25519-signed `Signature-Agent`, `Signature-Input`, and `Signature` headers for every outgoing request (both the shim and Playwright). The shim drives `auth_flow` per request and merges the resulting headers into the underlying curl_cffi call — same external behaviour as before, no change to `WebBotAuth` itself. Allows target servers to identify and verify the scraper as a legitimate bot. Requires the `cryptography` package.
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

#### `products.json` Pagination and 429→Playwright Escalation

`_fetch_all_shopify_products` walks the `/products.json` endpoint page by page (`?limit=250&page=N`) until a page returns fewer than `limit` products. Each page is fetched through a per-page escalation ladder (`_fetch_page_with_escalation`) that mirrors `BaseScraper.fetch_page_with_screenshot`:

1. One shim (curl_cffi) attempt. On a non-429 error, `raise_for_status()` surfaces immediately (no escalation).
2. On a 429 (or a `RequestError`), sleep 5s and escalate to Playwright for that page only.
3. Up to `max_retries` Playwright attempts with 5s/10s backoff; Playwright HTML is parsed back into JSON via BeautifulSoup.

After the [2026-08 curl_cffi swap](../operations/curl-cffi-swap-2026-08.md), the shim rarely returns 429 — it still does on hosts whose fingerprint throttle is stricter, and the Playwright fallback handles those. The ladder is unchanged so any host that 429s through the shim is still handled.

Escalation is tracked **per page**, not on an instance-level flag, so a recovered host re-attempts httpx on the next page instead of staying pinned to Playwright. On a complete failure of a page, the listing URL is appended to `_failed_listing_urls` so `create_diffjson_stock_updates` suppresses out-of-stock updates for that session — see [Scraper Log Analysis — July 2026 (Post-Fix)](../operations/scraper-log-analysis-2026-07-post-fix.md) and the [Playwright 429 Escalation Investigation](../operations/playwright-escalation-investigation-2026-07.md) for the bug history and the 2026-07-31 fix. Regression tests live in `TestShopify429Escalation` in `tests/unit/test_shopify_scraper.py`.

#### URL Normalisation for Non-ASCII Handles

`BaseScraper._normalize_url()` (static method) decodes percent-encoded characters in product URLs so that raw non-ASCII Shopify handles (e.g. Japanese product slugs returned directly by `/products.json`) match the percent-encoded form stored in existing bean JSON files (where the AI extracted the canonical page URL). This prevents duplicate bean entries for non-English roasters. The method uses `urllib.parse.unquote()` which is idempotent — already-decoded URLs remain stable. Normalisation is purely for in-memory set-membership comparison; the original URL form is preserved when writing to disk.

## Cross-Roaster Patterns & Gotchas (2026-08)

Recurring issues discovered while adding ~35 Top-100 roasters. See also `.opencode/skills/shopify-scraper/SKILL.md` and `.opencode/skills/non-shopify-scraper/SKILL.md`.

- **Shopify currency geolocation** — the most common failure. Shopify Markets serves converted prices to non-local clients (by IP / `Accept-Language`); the scraper's curl_cffi client often gets GBP/USD even when plain `curl` shows the home currency. Fix by pinning `store_currency` + `_currency_detected=True`, overriding `_fetch_all_shopify_products` to append `?country=XX` / `?currency=XXX`, and/or dropping the `Accept-Language` header. Examples: `heart.py`, `rosso.py`, `philocoffea.py`, `morgon.py`, `single_o.py`, `subtext.py`, `monogram.py`, `luna.py`, `intelligentsia.py`.
- **Prefer a curated coffee collection over `collections/all`** — `/collections/all/products.json` mixes coffee with equipment/merch/subscriptions. Use the site's own "coffee"/"beans" collection, or filter `product_type == "Coffee"` in `_extract_product_urls_from_store`.
- **Canonical URL + dedup after formatting** — many Shopify sites canonicalise to `/products/<handle>`; override `preprocess_product_url` to strip the collection segment. If you override `_extract_product_urls_from_store`, dedup on the formatted URLs (`self.deduplicate_urls(...)`) so products in multiple collections are counted once. **If you change a scraper's URL format, also override `_canonicalize_url`** so old-format history is still recognised — see [Changing a Scraper's Product URL Format](#changing-a-scrapers-product-url-format).
- **Token efficiency** — JSON-only (`scrape_product_pages=False` + `use_optimized_mode=True`) is cheapest; avoid `cache_product_pages=True` with `scrape_product_pages=False` (runs Playwright per product — slow). When the page adds fields, use `use_optimized_mode=False` + `preprocess_product_soup` pruning.
- **Non-Shopify platforms** — PrestaShop (server-rendered category + `data-product` JSON, narrow `.product__view`), GMO "shop-pro" (`?pid=` products, EUC-JP, `<p class="soldout">`), Square Online (cards have no hrefs → use `sitemap.xml` for discovery + Playwright detail), Japanese BASE (`/items/<id>`, Japanese sold-out text, `translate_to_english=True`).
- **Default currency GBP fallback** — `BaseScraper.__init__` looks up `default_currency` via `get_scraper_info(roaster_name)` keyed by display name, which misses hyphenated registry names and falls back to GBP; scrapers compensate by pinning the currency in `postprocess_extracted_bean`.
- **Bot-protected pages** — when product pages 401 to both curl and Playwright (e.g. Passenger), force JSON-only mode on the injected Shopify context.

### Tasting Kits: Flag, Don't Exclude

Since commit `6d5e1a8`, curated multi-coffee tasting kits / samplers / taster packs are no longer silently excluded from scraping — they are extracted, flagged, and held out of public search until an admin approves them. The base class no longer excludes kit tokens: `_get_excluded_url_patterns()` dropped `"sample"` and `"taster-pack"`, and `_get_excluded_product_name_categories()` dropped `"taster-pack"`. Only genuine equipment/services (`grinder`, `v60`, `subscription`, `gift-card`, capsules, apparel, …) remain excluded. The central equipment lists were also widened (2026-08) with dripper/brewer terms (`dripper`, `kettle`, `gooseneck`, `espresso-machine`, `brewer`, `canister`, `carafe`, `decanter`, `flask`, `paper-filter`, `filter-pack`, `brew-filter`); roaster-scoped `exclude_slugs` handle store-specific merch (e.g. Dear Green's books, tours, posters).

The hook set in `src/kissaten/scrapers/base.py`:

- `_get_tasting_kit_url_patterns() -> list[str]` — default
  `["taster-pack", "taster_pack", "sample-pack", "sampler", "tasting-kit", "tasting-set", "sample", "taster", "gift-box", "giftbox", "sample-box", "cupping-box"]`.
- `is_tasting_kit_url(url) -> bool` — lowercased substring match against those patterns.
- `_bean_name_is_tasting_kit(bean) -> bool` — matches the bean **name** against kit tokens (`sampler`, `sample pack/case/box`, `tasting kit/set`, `taster`, `gift box`, `coffee kit`, `cupping kit`). Catches kits whose URL handle carries no kit token (e.g. a product named "Around The World Coffee Sampler Gift Box" under a plain handle).
- `postprocess_review_flags(bean, url)` — a no-op hook roasters override to add roaster-specific kit/review classification; runs on every extracted bean right before the flags are applied.
- `_apply_product_flags(bean, url, is_new: bool = True)` — sets
  `bean.is_tasting_kit = bool(bean.is_tasting_kit) or self.is_tasting_kit_url(url) or self._bean_name_is_tasting_kit(bean)`, and sets
  `bean.requires_review = bool(bean.is_tasting_kit)` **only when `is_new=True`**. Stock-update diffs
  call the same helper with `is_new=False` so a previously-approved kit is never re-hidden.

Call sites (both with `is_new=True`): `scrape_with_ai_extraction` — right after `_extract_bean_with_ai`, before the `is_coffee_product_name` gate — and the Shopify JSON path in `shopify_base.py`.

~75 per-roaster scrapers were migrated: the seven kit tokens (`sample`, `sampler`, `sample-pack`, `sample-box`, `taster-pack`, `tasting-kit`, `tasting-set`) were removed from `self.exclude_slugs`, `excluded_patterns`/`excluded_products` lists, `_get_excluded_url_patterns()` overrides, and inline URL checks (e.g. manhattan_coffee.py's `if "tasting-kit" in url_lower: continue`). Kept: non-kit tokens and roaster-specific overrides that are *not* part of the kit sweep (e.g. subtext's `seasonal-sample`, roasticious's `taster`, ojo_de_cafe's `probierset`). Recognised kit-sweep exception: skylark_coffee.py still excludes `12-days-of-christmas` via a `super()._get_excluded_url_patterns() + ["12-days-of-christmas"]` override, while dropping the now-redundant `four-pack-sampler-mixed` path exclusion so that product is extracted and flagged.

Guidance for **new scrapers**: don't add `sample`/`sampler`/`taster-pack` to any exclude list — kit URLs should flow through and land in the review queue. Override `_get_tasting_kit_url_patterns()` only to add roaster-specific kit URL tokens. Rely on `_apply_product_flags` (called by the base paths) and keep `is_new=False` for stock updates. See [Tasting Kit Review Pipeline — 2026-08](../operations/tasting-kit-review-pipeline.md) and [`docs/KIT_REVIEW.md`](../../docs/KIT_REVIEW.md).

### Changing a Scraper's Product URL Format

Bean identity is the product **URL** — history (`_all_sessions_bean_files`) and
stock-update matching are keyed on it. If you change a scraper's URL format
(e.g. canonicalise `/collections/<slug>/products/<handle>` → `/products/<handle>`),
the historical bean JSON on disk still holds the old format. Without extra
handling the change has two bad effects:

1. **Re-scrape** — every product looks "new", so the full AI extraction runs
   again for products we already have.
2. **False out-of-stock** — the Shopify stock-update matcher
   (`ShopifyJsonScraper.create_diffjson_stock_updates`) compares the current
   catalog (new format) against history (old format); with zero overlap the
   old-format entries are treated as sold out.

The fix is the reusable **`_canonicalize_url(url)`** hook on `BaseScraper`. It
defaults to the identity (returns the URL unchanged) so only scrapers that
override it change behaviour. It is applied at every identity point — loading
history (`_load_existing_beans_in_current_session` /
`_load_existing_beans_from_all_sessions`), marking (`_mark_bean_as_scraped`),
and querying (`_is_bean_already_scraped_in_session` /
`_is_bean_already_scraped_historically` / `_is_bean_already_scraped_anywhere`)
— via `self._normalize_url(self._canonicalize_url(url))`. Because the same
canonicalised set feeds both re-scrape detection *and* the stock-update
matcher, a single override fixes both problems.

For a Shopify scraper canonicalising to `/products/<handle>`:

```python
def _canonicalize_url(self, url: str) -> str:
    return re.sub(r"/collections/[^/]+/products/", "/products/", url)

def preprocess_product_url(self, url: str) -> str:
    return self._canonicalize_url(url)  # DRY: the working URL is canonical too
```

Examples that needed this on rollout (2026-08): **Archers Coffee** and
**Flower Child Coffee** — their products appear in several collections
(`espresso-milk-coffees-2025`, `pour-over-coffees-2025`, `bespoke-blends-2025`;
`active-coffee`, `archive`), so each handle previously produced one URL per
collection (Archers ~203 duplicate beans, Flower Child ~20). Canonicalising by
handle collapses them. It does **not** merge distinct filter/espresso products —
those keep different handles and are represented within one bean via
`roast_profile` / `price_options`.

Regression tests: mark-then-query symmetry (mark the canonical form, then the
old collection forms count as scraped) and history-load detection (write an
old-format bean JSON, load it, assert the canonical URL is recognised) — see
`tests/unit/test_shopify_url_canonicalization.py`.

**Gotcha**: this prevents *future* duplicates and stops the re-scrape / false
out-of-stock on rollout, but any duplicate rows already in the DuckDB from
previous sessions are **not** retroactively cleaned — that needs a separate
dedup/cleanup pass.

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
