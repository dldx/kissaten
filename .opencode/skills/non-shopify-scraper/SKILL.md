---
name: non-shopify-scraper
description: Generate a Kissaten scraper for a non-Shopify coffee roaster site. Use when the user says "add a scraper for <store>", "new roaster <domain>", or supplies a homepage/collection URL and the site is not a Shopify store (no working products.json endpoint).
license: Proprietary
compatibility: Python 3.10+, uv, network access to the target store, curl, optional Playwright for JS-heavy sites, optional GOOGLE_API_KEY for AI extraction
allowed-tools: Bash(curl:*) Bash(python:*) Bash(playwright:*) Read Write Edit Grep Glob
---

# Non-Shopify Scraper Generator

## When to use
Use this skill when the user wants a new Kissaten scraper for a coffee roaster whose site does **not** expose a working `products.json` endpoint (or any other structured API that fits `ShopifyJsonScraper`). If the store is Shopify-hosted, use the `shopify-scraper` skill instead — that path is shorter and more reliable.

This skill covers the long tail of bespoke storefronts: Webflow, Squarespace, WooCommerce, Square Online, Subbly, custom React/Vue/Next.js, and the assorted CMS-driven sites that most specialty roasters actually run.

## Inputs the user must supply up front
Required:
- Store domain + at least one coffee collection/category URL (e.g. `https://roaster.com/collections/coffee`, `https://roaster.com/shop/coffee`, `https://roaster.com/store/filter-coffee`)
- Roaster name (the display string used everywhere)
- Country — must appear verbatim in `src/kissaten/database/roaster_location_codes.csv`
- Currency (ISO code)

Optional with defaults:
- `display_name`, `website`, `description` — derived from the URL/domain
- `exclude_patterns` — default: `subscription, gift-card, gift, wholesale, equipment, brewing, accessory, merchandise, sampler, taster-pack, apparel, mug, tumbler, hoodie, tshirt, capsules, pods, drip-bag, gift-voucher`
- `use_playwright` (default `False`), `translate_to_english` (default `False`), `use_optimized_mode` (default `False`)
- `use_ai_extraction` (default `True`) — see "AI extraction" below

## Files to read first (in this order)
Read **all** of these before writing code. The code may have changed since this skill was written.

Core contract and registry:
- `src/kissaten/scrapers/base.py` — `BaseScraper` contract, `extract_product_urls_from_soup`, `is_coffee_product_url`, `is_coffee_product_name`, `scrape_with_ai_extraction`, `create_diffjson_stock_updates`, `resolve_url`, `_get_excluded_url_patterns`, `_get_excluded_url_path_patterns`
- `src/kissaten/scrapers/registry.py` — `@register_scraper` semantics, country validator
- `src/kissaten/scrapers/__init__.py` — where the new import + `__all__` entry go
- `src/kissaten/database/roaster_location_codes.csv` — to validate country

Annotated template:
- `src/kissaten/scrapers/template.py` — start-here template with full workflow commentary

Model scrapers (load all five so you can compare and pick the best fit):
- `src/kissaten/scrapers/koppi.py` — minimal AI-extraction scraper (default model)
- `src/kissaten/scrapers/sw_roasting.py` — Playwright with `Cookiebot` consent dismissal
- `src/kissaten/scrapers/flames_coffee.py` — Playwright with proof-of-work challenge
- `src/kissaten/scrapers/one_half_coffee.py` — Playwright with infinite-scroll auto-scroll
- `src/kissaten/scrapers/cartwheel_coffee.py` — tabbed Webflow listing with custom selectors

Sold-out pattern references:
- `src/kissaten/scrapers/dumbo_coffee.py` — `out-of-stock` class detection (Shopify/Shopline)
- `src/kissaten/scrapers/the_underdog.py` — WooCommerce "Out of stock" text detection
- `src/kissaten/scrapers/the_roasting_shed.py` — Shopify "Sold out" text detection
- `src/kissaten/scrapers/rose_coffee.py` — Shopify "Sold out" text detection
- `src/kissaten/scrapers/lilo_coffee_roasters.py` — Japanese "SOLD OUT" text detection

## Workflow

1. **Read every file listed above.** Do not skip — the code may have changed since this skill was written.

2. **curl-first discovery.** Inspect the site before writing any code:
   ```
   curl -fsSL -A 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36' <collection_url> | head -c 50000
   ```
   Note the response status, the `<title>`, and the body length. Look for:
   - Bare HTML listing with product links visible in the source → use the **`koppi.py` model**.
   - Empty `<div id="root">` / no product links in the initial HTML → JS-rendered; switch to Playwright.
   - `cf-challenge`, `cf-chl-bypass`, or a `challenge_passed` cookie flow → use the **`flames_coffee.py` model**.
   - `Cookiebot` / `cookieconsent` / `onetrust` banner that gates product content → use the **`sw_roasting.py` model**.
   - Pagination indicators: `?page=2`, a `Load more` button, or an infinite-scroll sentinel → use the **`one_half_coffee.py` model**.
   - `data-w-tab` attributes or similar tabbed structure → use the **`cartwheel_coffee.py` model**.
   - If none of the heuristics clearly match, ask the user which of the 5 models best fits, presenting a one-line summary of each.

3. **Sold-out filtering — apply the checklist** during `_extract_product_urls_from_store`. Record the chosen pattern as a `# Sold-out detection: <pattern>` comment in the generated file:
   1. **URL filter param (cheapest, preferred).** If the site accepts `?filter.v.availability=1` (Shopify) or any equivalent "in stock only" query param, append it to the `get_store_urls()` URLs. Done — no further filtering needed at the link level.
   2. **Class detection** (Shopify, Shopline, custom). Walk the link's parent and sibling tree; skip the link if any element has a class containing `out-of-stock`, `sold-out`, or `oos`. Reference: `dumbo_coffee._check_if_sold_out`.
   3. **Text detection** (WooCommerce, Square, Subbly, etc.). Check the link's parent text for `Sold out` / `Out of stock` / `SOLD OUT`. References: `the_underdog.py`, `the_roasting_shed.py`, `rose_coffee.py`, `lilo_coffee_roasters.py`.

   Sold-out filtering must run **before** `is_coffee_product_url`, or excluded products will leak past the stock check.

4. **Ask the user only for any input fields they have not yet supplied.** Do not re-ask for fields they have already given you (domain, URL, country, currency, roaster name, etc.).

5. **Generate `src/kissaten/scrapers/<slug>.py`** modeled on the chosen reference scraper. Concrete rules:
   - Use the roaster name verbatim in both `@register_scraper(roaster_name=…)` and `super().__init__(roaster_name=…)`. They must be byte-identical.
   - Always subclass `BaseScraper` directly (not `ShopifyJsonScraper`).
   - Always initialize `CoffeeDataExtractor` and call `scrape_with_ai_extraction`. This is the default — it handles the long tail of page layouts better than hand-rolled parsing.
   - Implement `get_store_urls()` (returns the collection URLs to crawl).
   - Implement `_extract_product_urls_from_store()` with the chosen sold-out filtering pattern.
   - Implement `_scrape_new_products()` that delegates to `scrape_with_ai_extraction` with the right `use_playwright` / `use_optimized_mode` / `translate_to_english` flags.
   - If the chosen model needs a custom `fetch_page` (cookie dismissal, challenge solving, infinite scroll, tab picking), copy that override verbatim and adapt the selectors/strings to the new site.
   - Add `# Sold-out detection: <pattern>` comment near the top of `_extract_product_urls_from_store`.

6. **Auto-apply the edit to `src/kissaten/scrapers/__init__.py`:** add the import line in alphabetical order with the other imports and add the class name to `__all__`. Both edits in one file.

7. **Run the registry validation command** and report output. If it raises, fix the error and re-run.

8. **Remind the user of the optional smoke-test command.**

## Critical invariants
- `roaster_name` in `super().__init__(…)` must exactly equal `roaster_name=` in `@register_scraper(…)` — enforced by `BaseScraper._validate_roaster_name` (base.py lines 34–67).
- `country` must match a row in `roaster_location_codes.csv` — the registry model validator will raise at decoration time if not.
- `name=` in `@register_scraper(...)` (the CLI name) must be unique across the registry. Check `get_registry().is_registered(name)` first if reusing a name.
- Sold-out filtering must be applied **before** `is_coffee_product_url` filtering, or excluded products will leak past the stock check.
- If the model uses Playwright, prefer `await super().fetch_page(*args, **kwargs)` for the base call and only override what you need (cookie dismissal, scroll loop, etc.). This keeps rate limiting, retry, and session accounting intact.

## AI extraction
- Default to AI extraction (`requires_api_key=True`, instantiate `CoffeeDataExtractor`, call `scrape_with_ai_extraction`). This is the right call for ~95% of roaster sites and keeps the generated file under ~150 lines.
- Only deviate to manual HTML parsing if the user explicitly asks for it, or if the roaster's product page has no useful text content (e.g. a pure JavaScript app where the AI has nothing to read).
- `translate_to_english=True` is the right call for non-English sites (Japan, Korea, Taiwan, China, France, Germany, etc.) — it dramatically improves AI extraction quality.

## Validation command
```
uv run python -c "from kissaten.scrapers.<slug_module> import <ClassName>; from kissaten.scrapers.registry import get_registry; print(get_registry().get_scraper_info('<slug>'))"
```

## Optional smoke test
```
uv run python -m kissaten.cli scrape <slug> --limit 1 --api-key $GOOGLE_API_KEY
```

## Out of scope
Committing, writing per-roaster tests, surfacing this skill in `AGENTS.md`, scraping sites behind login walls or authenticated user areas, multi-currency / multi-locale variants of the same roaster.
