---
name: shopify-scraper
description: Generate a Kissaten Shopify JSON scraper from a user-provided products.json URL. Use when the user says "add a Shopify scraper for <store>", "new roaster <domain>", or supplies a products.json link.
license: Proprietary
compatibility: Python 3.10+, uv, network access to the target store, optional GOOGLE_API_KEY for AI extraction
allowed-tools: Bash(curl:*) Bash(python:*) Read Write Edit Grep Glob
---

# Shopify Scraper Generator

## When to use
Use this skill when the user wants a new Kissaten scraper for a Shopify-hosted coffee roaster and they already know (or can give you) the `products.json` endpoint. Do **not** use for non-Shopify stores — they need a different scraper shape.

## Inputs the user must supply up front
Required:
- Store domain and `products.json` endpoint (e.g. `https://roaster.com/collections/coffee/products.json`)
- Roaster name (the display string used everywhere)
- Country — must appear verbatim in `src/kissaten/database/roaster_location_codes.csv`
- Currency (ISO code)

Optional with defaults:
- `display_name`, `website`, `description` — derived from the URL
- `exclude_slugs` — default: `subscription, gift-card, gift, wholesale, equipment, brewing, accessory, merchandise, sampler, taster-pack, apparel, mug, tumbler, hoodie, tshirt, capsules, pods, cold-brew-cans, easy-pour`
- `scrape_product_pages` (default `True`), `use_optimized_mode` (default `False`). ⚠️ `scrape_product_pages=True` with `use_optimized_mode` unset/False sends the full page HTML to the AI and is token-hungry — read "Token efficiency" below before combining them.

## Choosing the right products.json collection and product URL

**Identify the most optimal Shopify collection first rather than defaulting to `all`.**
`collections/all/products.json` mixes beans with gift cards, subscriptions, equipment, merch, and other non-coffee items, which forces a long `exclude_slugs` list to filter back down to coffee. When a roaster curates a dedicated coffee collection (e.g. `/collections/coffee/products.json`, `/collections/our-coffee/products.json`, `/collections/filter-coffee/products.json`), prefer it — it is cleaner, cheaper (fewer products, less AI token usage), and naturally limits to beans. Discover the roaster's available collections (e.g. from the site nav, sitemap, or homepage) and pick the most coffee-specific one before falling back to `all`.

**Identify what the website itself uses as its product URL instead of assuming the collection is part of the URL.** `ShopifyJsonScraper` builds product URLs from the `products.json` URL base, so using a collection `products.json` yields `/collections/<name>/products/<handle>` — but many roasters' real/canonical product pages are just `/products/<handle>` (no collection segment). Check what URL the site actually serves for a product (e.g. curl the `handle` or click a product on the live site) and, if it is the no-collection form, override `preprocess_product_url` to strip the collection segment (reference `aviary.py` for the override pattern). Keep the scraper's product URLs aligned with the site's real URLs.

## Files to read first (in this order)
- `src/kissaten/scrapers/shopify_base.py` — base class contract and hooks
- `src/kissaten/scrapers/apollons_gold.py` — minimal example
- `src/kissaten/scrapers/aviary.py` — minimal example with URL normalization
- `src/kissaten/scrapers/blue_tokai_coffee.py` — `preprocess_product_url` example
- `src/kissaten/scrapers/registry.py` — `@register_scraper` semantics, country validator
- `src/kissaten/scrapers/base.py` lines 34–67 — the `roaster_name` registry-match check
- `src/kissaten/scrapers/__init__.py` — where the new import + `__all__` entry go
- `src/kissaten/database/roaster_location_codes.csv` — to validate country

## Workflow
1. Read every file listed above. Do not skip — the code may have changed since this skill was written.
2. Confirm `curl -fsSL <products.json url> | jq '.products | length'` returns a sensible number. Note the currency if visible in the JSON.
3. **Research a representative product's information density before choosing the scrape shape.**
   Pick one real coffee product (prefer the one with the richest variants) and figure out how much bean detail lives where:
   - Inspect its JSON entry: `curl -fsSL <products.json url> | jq '.products[0]'` and record which fields the payload carries.
   - Open the product's detail page and **take a screenshot** of the rendered page with the shared helper — `uv run python scripts/screenshot_url.py "<product_url>" /tmp/opencode/shot.png` (the shared helper captures full-page screenshots and triggers lazy content automatically by default; pass `--no-scroll-lazy` to disable and `--cookie-selector "<banner selector>"` when a cookie banner blocks content) — and actually look at the screenshot.
   - Compare what the JSON carries vs. what the rendered page shows vs. the full `CoffeeBean` schema in `src/kissaten/schemas/coffee_bean.py`. For each field, record whether it appears (a) in the JSON, (b) only on the rendered page, or (c) nowhere: `description`; origin `country`/`region`/`producer`/`farm`/`elevation_min`/`elevation_max`/`latitude`/`longitude`/`process`/`variety`/`harvest_date`; cost-transparency fields (`fob_price`, `farm_gate_price`, `price_paid_to_producer`, `price_currency`, `importer_name`); `roast_level`; `roast_profile` (Espresso/Filter/Omni/Both); `cupping_score`; `tasting_notes`; `is_decaf`; extra `price_options` (weight/price); `image_url`.
   - Set the scrape mode from the result: `scrape_product_pages=False` (JSON-only, cheapest) when the JSON already carries the fields; if the page exposes fields the JSON lacks, use `scrape_product_pages=True` and pick the token-efficient path per "Token efficiency" below — `use_optimized_mode=True` when there is no accordion/hidden info, or `use_optimized_mode=False` combined with a `preprocess_product_soup` prune when there is.
   - **Carousel guard:** if the product page may hold information behind a carousel, tabs, accordion, "read more"/show-more, or other swipeable or lazy-loaded UI (e.g. spec sheets or tasting notes that are only slides or hidden panels), **do not proceed automatically — ask the user a question first.** Offer them the choice between (a) making the scraper use Playwright to click/scroll through the carousel to capture the hidden fields, or (b) shipping with only the statically visible content.
4. Ask the user only for any input fields they have not yet supplied.
5. Generate `src/kissaten/scrapers/<slug>.py` modeled on `apollons_gold.py` (default) or `aviary.py` (if URL normalization is needed). Use the roaster name verbatim in both `@register_scraper(roaster_name=…)` and `super().__init__(roaster_name=…)`.
6. Auto-apply the edit to `src/kissaten/scrapers/__init__.py`: add the import line in alphabetical order with the other imports and add the class name to `__all__`.
7. Run the registry validation command and report output.
8. Remind the user of the optional smoke-test command.

## Token efficiency: `scrape_product_pages` × `use_optimized_mode`

Do **not** leave `scrape_product_pages=True` with `use_optimized_mode=False` (or unset) as a default: that sends the entire product-page HTML to the AI for every product, which burns a lot of tokens.

Decide per store after the research step in the Workflow:

- **Prefer `use_optimized_mode=True`** when there is no accordion/hidden information. The AI then extracts from the injected Shopify JSON context (the product `body_html`/variants) rather than the full page HTML, which is much cheaper. Good when the page adds nothing the JSON lacks.
- **Use `use_optimized_mode=False` only when the page genuinely carries information the JSON lacks** (e.g. bean details behind accordions, an SCA cupping score on the page, or spec sheets). When you do, you **must** also override `preprocess_product_soup` to prune the page to just the sections holding that extra info — that is what keeps token cost under control. Model it on the Apricity scraper (`src/kissaten/scrapers/apricity_coffee.py`), which keeps only the `div.product__accordion` elements.
- **Keep `scrape_product_pages=False`** (pure JSON-only) whenever the JSON is sufficient — the cheapest option.

Note: `preprocess_product_soup` runs before the Shopify product JSON is injected (`_inject_shopify_context`), so pruning to a minimal soup still preserves the product name/price/variants for the AI.

## Critical invariants
- `roaster_name` in `super().__init__(…)` must exactly equal `roaster_name=` in `@register_scraper(…)` — enforced by `BaseScraper._validate_roaster_name`.
- `country` must match a row in `roaster_location_codes.csv` — the registry model validator will raise at decoration time if not.
- `exclude_slugs` use substring match against the Shopify product `handle` (see `shopify_base.py`).

## Validation command
```
uv run python -c "from kissaten.scrapers.<slug_module> import <ClassName>; from kissaten.scrapers.registry import get_registry; print(get_registry().get_scraper_info('<slug>'))"
```

## Optional smoke test
```
uv run kissaten test-scraper <slug>
```
This tests connectivity only and does not require a Google API key or save any data.

## Out of scope
Committing, writing per-roaster tests, surfacing this skill in `AGENTS.md`.
