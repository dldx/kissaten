---
type: "Reference"
title: "Extraction Audit — Structured Data Left on the Table — 2026-09"
description: "Audit of 16,675 bean JSON outputs (14,940 unique beans) against 32,858 cached raw pages: 9,319 beans matched a cached page and 3,362 page-has-it/JSON-doesn't signals were found (~2,734 verified real). Biggest causes: a shared Squarespace fetch_page keep_meta whitelist that drops og:image (15 scrapers, ~170 image_url misses), JSON-only Shopify scrapers whose pages hold spec tables the AI never sees, optimized-mode scrapers where products.json context replaces the page (cafēn price_options, north_star altitude), custom pruning hooks that delete spec sections (dear_green, moklair, fathers, terres_de_café), and tanat_coffee (341 misses/167 beans). Includes per-scraper rankings, field-level precision, quick wins and best-in-class scrapers."
openwiki_generated: false
---

# Extraction Audit — structured data left on the table (2026-09)

**Date:** 2026-09-21
**Scope:** 16,675 bean JSON files in `data/roasters/` (14,940 unique bean URLs after dedupe), 32,858 cached raw pages in `data/cache/roasters/`, 571 registered scrapers.
**Question:** which scrapers are not extracting the maximum possible structured data from the original product pages?

## TL;DR

- Of 14,940 unique beans, **9,319 (63%) match a cached raw page** and were audited against it. Page-side detectors (16 field signals, evidence snippets) found **3,362 recent "page has it, JSON doesn't" signals**. An exact-pair verification sample (n=60, stratified, seed 42) estimates **~2,734 (81%) are real** after removing false positives and 13 generic `og:image` rows.
- Overall strict recall is **≈0.94**, but misses are concentrated: **2,589 of 9,319 audited beans (28%) have at least one missed structured field**, and a handful of scrapers account for most of it (top 30 ≈ 60% of weighted misses).
- Biggest actionable classes:
  1. A shared Squarespace `fetch_page` metadata whitelist **drops `og:image`** in **15 scrapers** (~170 image_url misses; spec prose is pruned too). One-line fix per scraper.
  2. **JSON-only Shopify scrapers** (`scrape_product_pages=False`) whose product pages carry spec tables (process/variety/elevation/SCA) that never reach the AI: cworks, elsewhere_coffee, colonna, botz, 44_north and ~50 more.
  3. **Optimized-mode scrapers** where the page is replaced by `products.json` context, hiding page-only weights/specs: cafēn, north_star, aliena, zeff, celsius, old_spike, coffea_circulor, caravan, cult, mirra.
  4. **Custom pruning/narrowing hooks** that delete spec sections before the AI sees them: dear_green, moklair, fathers, terres_de_café, 44_north.
  5. **Scale outlier:** tanat_coffee — 341 strict misses across 167 beans (harvest 141, cupping 119, image 34); WooCommerce tab content + translation, no deterministic parsing.
- Highest-value fields to fix: **image_url (~812 real), harvest_date (732), cupping_score (~303), description (169), variety (161), price_options (147 variants + page-weight misses), elevation (~175)**.

## Fix status — 2026-09-21

Quick wins **1 and 2 implemented and live-verified** (uncommitted working-tree changes):

- **Fix 1 (Squarespace `keep_meta` + spec prose):** added `og:image` to the meta whitelist and appended a new `BaseScraper._extract_product_description_tag()` (`.product-description` etc.) to the compact soup in all 15 affected scrapers: `blue_hour`, `swan_song`, `coopers_coffee`, `spaceboy`, `fika`, `full_court_press`, `fortitude`, `51_degrees_north`, `opal_coffee_roasters`, `echelon`, `forge`, `smugglers_drop`, `sunday_coffee`, `tilted`, `pala_kaffebrenneri`. This covers 184 audited beans / 440.5 weighted strict misses, including 170 `image_url` misses. The canonical pattern in `.opencode/skills/squarespace-scraper/SKILL.md` was updated to match.
- **Fix 2 (global deterministic image_url backfill):** `BaseScraper._extract_image_url_from_soup()` (og:image → og:image:secure_url → twitter:image → link[rel=image_src] → JSON-LD `Product.image`), recorded at raw-fetch time in `_page_image_urls` (before any subclass `fetch_page` pruning) and backfilled in `_extract_bean_with_ai`; `ShopifyJsonScraper` additionally backfills from `products.json` `images[0].src` / variant `featured_image` for JSON-only scrapers. Addresses the ~812 real `image_url` misses across 182 roasters for all future extractions.
- **Live smoke:** `kissaten test-scraper blue-hour` now yields `image_url` + `process: Natural`, `variety: Gesha`, `elevation: 1800-2000` (previously all empty); `kissaten test-scraper botz` yields `image_url` backfilled from products.json.
- **Tests:** `tests/unit/test_extraction_backfill.py` (43 new tests, incl. a parametrized compact-soup test over all 15 scrapers); `tests/unit/test_opal_coffee_roasters.py` updated (it previously asserted the buggy og:image-drop behavior). Full unit suite: 1380 passed.
- **Not yet done:** existing bean JSONs are unchanged — the incremental pipeline only re-extracts new products, so affected roasters need `kissaten scrape <scraper> --force-full-update` (or the next forced full pass) for the improved fields to land in the data. Quick wins 3–5 (variant-based `price_options`, labeled-field regex capture, worst-scraper re-scrapes) remain open.

## Method

1. **Output side (B1).** All bean JSONs deduped to the latest per `(roaster_slug, url)`; per-field fill rates per roaster; scraper config parsed from source with AST (base class, `scrape_product_pages`, `use_optimized_mode`, `cache_product_pages`, overrides).
2. **Page side (B2).** Joined beans to cached tarballs (`metadata.json` + `page.html`): exact canonical URL (8,520) or product handle (799); 5,621 unmatched (mostly pre-2026-01-05, before cache retention). 97.8% of matched pairs come from the same session (all within 45 days after filtering). For each pair, 16 detectors looked for labeled structured data in product-scoped page text, embedded Shopify product JSON, JSON-LD, tags and variants. Every signal carries a verbatim snippet + source.
3. **Aggregation (B3).** Strict score uses only low-false-positive fields and weights; soft signals (producer/farm, roast_profile, roast_level, importer, text-derived price weights) are reported but excluded from rankings. Session-staleness filtered to |Δ| ≤ 45 days.
4. **Verification (T1–T3).** 60 stratified exact-pair rows (5 per strict field) were re-opened and judged; per-field precision estimated; global `og:image` reuse analysis; root-cause code inspection of the 15 worst scrapers.
5. **Limits.** Detector-based (a page signal is a labeled match, not an LLM judgement); text/JSON-LD only (image-only spec sheets are invisible, so true gaps are ≥ these numbers); 37% of beans have no cached page; 113 roasters never matched a page.

## Field-level results (9,319 matched beans)

Raw misses are the recent (|Δ|≤45d) strict-signal count; precision is from the n=5-per-field verification sample.

| Field | Page has it | Raw misses | Est. precision | Est. real misses | Main cause |
|---|---|---:|---:|---:|---|
| image_url | 8,590 | 825 | 1.00 | 812 | og:image not captured (whitelist/JSON-only/custom fetch) |
| harvest_date | 1,435 | 732 | 1.00 | 732 | "Harvest: YYYY" labels ignored (tabs, prose) |
| cupping_score | 984 | 505 | 0.60 | 303 | "SCA/Cupping Score" labels ignored; some nav-text FPs |
| transparency (FOB/farm-gate/paid) | 455 | 291 | 0.20 | 58 | detector matches marketing "transparency"; real data on ~15 stores |
| elevation | 5,064 | 194 | 0.90 | 175 | "Altitude: 1800-2000 MASL" pruned/JSON-only |
| description | 6,262 | 169 | 1.00 | 169 | JSON-LD/body_html longer than bean description |
| variety | 4,207 | 161 | 1.00 | 161 | "Varietal:" labels ignored |
| price_options (variant weights) | 7,946 | 147 | 1.00 | 147 | page has more weights than bean |
| country_region | 6,044 | 125 | 0.30 | 38 | mostly page headings/boilerplate (noisy detector) |
| process | 7,551 | 104 | 0.50 | 52 | related-product names inflate detector |
| tasting_notes_present | 3,971 | 98 | 0.80 | 78 | placeholder/label without real notes |
| latlon | 22 | 11 | 0.80 | 9 | branding "Latitude 44° North" FPs |
| **Total** | — | **3,362** | **0.76** | **~2,734** | |

Soft signals excluded from ranking but real gaps worth review: `producer_or_farm` 578 raw misses, `roast_profile` 833, `roast_level` 240 (detector precision low; spot checks showed both real label-based misses and related-product-text false positives).

## Worst-offender scrapers

### By strict misses per audited bean (recent, n_joinable ≥ 5)

| # | roaster | n | misses/bean | recall | top missed fields | cause |
|---|---|---:|---:|---:|---|---|
| 1 | blue_hour | 11 | 5.27 | 0.28 | img 11, elev 9, proc 7 | Squarespace keep_meta drops og:image/spec |
| 2 | swan_song_coffee_roasters | 15 | 4.63 | 0.60 | img 15, trans 11, harv 8 | Squarespace keep_meta |
| 3 | cworks | 30 | 3.80 | 0.59 | cupp 19, proc 16, elev 13 | JSON-only; pages cached but unused |
| 4 | coopers_coffee | 9 | 3.17 | 0.59 | img 8, tast 4, proc 3 | Squarespace keep_meta |
| 5 | spaceboy_coffee | 8 | 2.94 | 0.49 | img 7, proc 4, var 2 | Squarespace keep_meta |
| 6 | fika | 18 | 2.64 | 0.57 | img 18, desc 7, tast 5 | Squarespace keep_meta |
| 7 | elsewhere_coffee | 20 | 2.25 | 0.76 | elev 12, proc 4, var 4 | JSON-only; page-only spec sheet |
| 8 | dear_green | 36 | 2.22 | 0.66 | elev 16, harv 16, cupp 9 | preprocess keeps `div.description` only |
| 9 | colonna | 15 | 2.20 | 0.75 | elev 11, img 2, tast 2 | JSON-only + fragment URLs |
| 10 | full_court_press | 44 | 2.14 | 0.72 | img 42, harv 28, price 5 | Squarespace keep_meta |
| 11 | fortitude | 12 | 2.12 | 0.77 | img 11, harv 9 | Squarespace keep_meta |
| 12 | tanat_coffee | 167 | 2.04 | 0.79 | harv 141, cupp 119, img 34 | WooCommerce tabs, wide-page AI + translate |
| 13 | 51_degrees_north | 8 | 2.00 | 0.78 | img 8, ctry 4 | Squarespace keep_meta |
| 14 | moklair | 13 | 1.88 | 0.73 | cupp 12, price 5, img 4 | narrows to `div#product-*`; tabs invisible |
| 15 | north_star_coffee_roasters | 25 | 1.80 | 0.81 | elev 12, ctry 9, var 4 | optimized mode replaces page with JSON context |
| 16 | fathers | 41 | 1.68 | 0.75 | img 40, price 25, trans 4 | custom `_render_product_snippet` drops images/variants |
| 17 | cafēn | 65 | 1.54 | 0.85 | price 59, harv 6, trans 3 | optimized JSON context hides 1g/50g variants |
| 18 | terres_de_café | 101 | 1.46 | 0.82 | cupp 100, price 79, img 13 | default-variant-only extraction |
| 19 | cartwheel_coffee | 35 | 1.33 | 0.83 | harv 30, proc 5, var 3 | labels present but unparsed |
| 20 | botz | 74 | 1.17 | 0.84 | img 54, desc 8 | JSON-only; products.json images/variants unused |

### By absolute strict misses (top 12)

tanat_coffee 341 · terres_de_café 147.5 · cworks 114 · cafēn 100 · hydrangea_coffee_roasters 96.5 · full_court_press 94 · botz 86.5 · dear_green 80 · swan_song_coffee_roasters 69.5 · fathers 69 · blue_hour 58 · coffea_circulor 58 · fika 47.5 · cartwheel_coffee 46.5 · elsewhere_coffee 45 · north_star_coffee_roasters 45.

## Root causes in detail

### 1. Squarespace `keep_meta` whitelist drops `og:image` (15 scrapers, ~170 image_url misses)

15 modules share a copy-pasted `fetch_page` compact-soup helper whose whitelist is `{og:title, og:description, og:url, og:type, product:price:amount, product:price:currency, product:availability}` — **`og:image` is absent**, so the image URL never reaches the AI, and the page is reduced to meta + parsed variants, so spec prose is pruned too. Affected: `full_court_press` (42), `fika` (18), `swan_song` (15), `blue_hour` (11), `fortitude` (11), `sunday_coffee` (10), `echelon` (9), `coopers_coffee` (8), `fifty_one_degrees_north` (8), `tilted` (8), `spaceboy` (7), `pala_kaffebrenneri` (5), `smugglers_drop` (5), `forge` (3), `opal_coffee_roasters`.

### 2. JSON-only Shopify scrapers with page-only data (59 scrapers)

`scrape_product_pages=False` means the AI sees only `products.json`. But many stores put the real spec sheet on the rendered page (process/variety/altitude/SCA/harvest) and even the products.json `images`/`variants[].grams` are not surfaced deterministically. Examples: cworks (SCA scores, process, altitude on page), elsewhere_coffee, colonna, botz (cached products.json has images + 340 g variant; bean has `image_url=None`, 250 g only), 44_north (page variants 227/340/454/907/2268 vs bean 4 options), cartwheel, hardlines, luna, bean_&_bean, kaffeemacher. Many of these have `cache_product_pages=True` — the pages were captured but never sent to the AI.

### 3. Optimized mode + no `preprocess_product_soup` override

With `use_optimized_mode=True` and no custom soup hook, Shopify scrapers send JSON context instead of the page. Page-only specs/variants are invisible: northern_star (altitude/country), cafēn (59 price-option misses: page has 1 g/50 g variants absent from the JSON context), aliena, zeff, celsius, old_spike, coffea_circulor, caravan, cult, mirra.

### 4. Custom pruning/narrowing drops spec sections

- `dear_green`: preprocess keeps only `div.description`; the `ul.metafields-list` spec sheet (elevation, harvest, SCA) is inconsistently captured (elevation 16/17 missed).
- `moklair`: `fetch_page` narrows to `div#product-*`; WooCommerce tab content (SCA, extra weights) invisible.
- `fathers`: custom `_render_product_snippet` keeps name/URL/price/description only — per-variant image URLs and weights dropped (40 image_url, 25 price_options).
- `terres_de_café`: only the default variant is captured (79 price_options, 100 cupping signals — the latter mostly site category nav, so ~60 after adjustment).
- `44_north`: page variants not mapped to `price_options` (12).

### 5. Wide-page AI at scale

`tanat_coffee` (167 audited beans, 341 strict misses): full page + `translate_to_english=True`, no pruning, no deterministic label parsing. "Harvest 2025/2026" and cupping scores in WooCommerce tabs are missed at scale; og:image is not captured either.

### 6. Cross-cutting field gaps

- **harvest_date** (732 real): stores print "Harvest: 2025/2026" — a one-regex capture; biggest: tanat, nomad, rogue_wave, cartwheel, full_court_press, terraform, substance_café, nylon, blendin, dear_green, hola, rose, scenery, plot_roasting, oma.
- **cupping_score** (~303 real): "SCA 85", "Cupping Score: 86.50"; biggest: tanat, bean_&_bean, skylark, cworks, two_chimps, moklair, ozone, smith_street, archers.
- **transparency**: detector is 80% false positive (marketing "transparency"); real FOB/farm-gate/paid-to-producer data exists on drop_coffee_roasters, coffee_collective, quaffee, slow_coffee, redemption, seven_seeds, swan_song, glass, scenery, standout, blossom, fjord, archers, coaltown, muyu (counts need manual review).
- **description**: beans truncated vs JSON-LD/body_html (mame_roastery 26, coffea_circulor 15, archers 11, april, botz, momos, blue_hour, fika).
- **variety**: "Varietal:" labels missed (hydrangea 28/192, cworks 12/17, dear_green 8/10, tanat 6/166, archers 5/117).
- **latlon**: negligible (22 page signals).

## Quick wins (deterministic, no prompt changes)

1. **add `og:image` to the 15 `keep_meta` whitelists** (~170 misses) and keep spec prose in those scrapers — biggest single mechanical win.
2. **Build `image_url` from `og:image`/JSON-LD/image data in the extraction flow** for the rest: botz 54, fathers 40, tanat 34, red_rooster 19, machhörndl 14, hydrangea 13, people's_possession 13, terres_de_café 13, the_barn 13, coffee_lab 12, fuglen 12, blue_hour 11, fortitude 11, kaffeemacher 11, jbc 10, koppi 10, opal 10 (≈812 real signals).
3. **Map Shopify `variants[].grams/price` to `price_options` deterministically**: mobydick 96, terres_de_café 79, cafēn 59, mad_heads 43, coffee_lab 34, terraform 29, s&w_roasting 28, substance_café 27, fathers 25, tim_wendelboe 24, coffee_county 22, coffea_circulor 19, five_elephant 17, 44_north 12.
4. **Regex-capture labeled fields after AI extraction**: `Harvest[: ]+(20\d\d)`, `Cupping/?SCA[^0-9]*(8\d(\.\d+)?|9\d)`, `Altitude[:\s]+\d+`, `Varietal[s]?[:\s]+\w+`, `Process[:\s]+\w+`.
5. **Re-scrape the 15 worst-per-bean scrapers first** (blue_hour, swan_song, cworks, coopers, spaceboy, fika, elsewhere, dear_green, colonna, full_court_press, fortitude, tanat, 51_degrees_north, moklair, north_star) — or turn on page fetching with spec-preserving pruning for them.

## Best in class (recall = 1.00 on ≥10 audited beans)

alchemy_coffee, assembly_coffee_london, balloon_coffee_roasters, beberry_coffee, caretta_coffee, doubleshot, epoch_chemistry, ethica_coffee_roasters, fidela, formative_coffee, kaffa__sk_, lang_ra_kaffebrenneri, leaves_coffee_roasters, native_coffee_company, new_ground_coffee, onibus, origin_coffee_roasters, parallel, pilot_coffee_roasters, replica, shokunin_coffee_roasters, simple_kaffa, subtext, the_source_coffee_roasters, twoday_coffee_roasters.

## Caveats

- Page audit coverage: 9,319/14,940 beans (63%). 6,044 rows predate cache retention (2026-01-05) or have no cached product page; 113 roasters never matched (dak_coffee_roasters 121 beans, the_naughty_dog 110, glen_lyon 59, prolog_coffee 53, coffee_compass 47, code_black 45, passenger 43, ...).
- 118 scraper-config roasters have no beans in this dataset (registered, never scraped).
- Detector precision varies; **transparency (0.20), country_region (0.30), process (0.50) need human review**; strict rankings exclude those plus producer_or_farm/roast_profile.
- Cache retention starts 2026-01-05; results describe that window. Detectors read text/JSON-LD/embedded JSON only — image-only spec sheets (e.g. Terarosa) are not counted, so true gaps are ≥ these numbers.
- Artifacts: audit scripts and raw outputs live in `/tmp/opencode/extraction_audit/` (`b1_fill_rates.py`, `b2_page_audit.py`, `b3_aggregate.py`, `verification.md`, `verification_samples.md`, `final_tables.md`, `summary_b1.md`/`b2.md`/`b3.md`, parquet/CSV tables).

## Side observations

- `peaberry.py` is registered but not imported in `scrapers/__init__.py`, so it never registers at runtime (570 vs 571 parsed modules).
- `kafferaven` data dir corresponds to module `kaffer_ven` (`directory_name` derivation for "Kafferäven").
- `tanat_coffee/20251021/liberica_champagne_yeast...json` is truncated (JSONDecodeError) — one corrupt bean output.