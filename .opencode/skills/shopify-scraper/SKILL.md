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
- `scrape_product_pages` (default `True`), `use_optimized_mode` (default `False`)

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
3. Ask the user only for any input fields they have not yet supplied.
4. Generate `src/kissaten/scrapers/<slug>.py` modeled on `apollons_gold.py` (default) or `aviary.py` (if URL normalization is needed). Use the roaster name verbatim in both `@register_scraper(roaster_name=…)` and `super().__init__(roaster_name=…)`.
5. Auto-apply the edit to `src/kissaten/scrapers/__init__.py`: add the import line in alphabetical order with the other imports and add the class name to `__all__`.
6. Run the registry validation command and report output.
7. Remind the user of the optional smoke-test command.

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
uv run python -m kissaten.cli scrape <slug> --limit 1 --api-key $GOOGLE_API_KEY
```

## Out of scope
Committing, writing per-roaster tests, surfacing this skill in `AGENTS.md`.
