---
type: "Reference"
title: "Scraper Token Consumption Investigation — Terarosa & Bluebird — 2026-08-10"
description: "Why the Terarosa and Bluebird scrapers burned so many AI tokens (optimized mode on unpruned 140-490 KB pages + a never-saved/re-scraped-every-run loop) and the implemented fixes: Bluebird Elementor pruning (~490->~5 KB), Terarosa product-box pruning (~137->~4 KB), Terarosa discovery-time junk filter (bag appears on all 6 category grids), the Terarosa lazy-load screenshot fix (origin sheet is image-only; 15,615px spec wall was blank in captures), and live verification against stored *.json incl. a full end-to-end rerun."
openwiki_generated: false
---

# Scraper Token Consumption Investigation — Terarosa & Bluebird (2026-08-10)

> **Status (2026-08-10)**: Investigation complete; fixes for **both scrapers implemented
> and verified live** — Bluebird soup pruning, Terarosa soup pruning, Terarosa
> discovery-time junk filter, and the Terarosa lazy-load screenshot fix (all below).
> Open items: the Bluebird/Terarosa never-save/re-scrape loop and Terarosa run
> reliability (≈21/30 runs die early on the Playwright homepage fetch).
> Source: `logs/scrape.log` (204,780 lines / 16 MB, covering 2026-07-10 → 2026-08-10).
> The whole file was loaded in Python for analysis; only small slices were read into model context.

## TL;DR

Both scrapers (a) run the AI extractor in **optimized mode** — `gemini-2.5-flash` + a **full-page PNG screenshot** + the **entire unpruned product-page HTML** on every call — and (b) **re-scrape the same products every run** because the extracted beans are never saved, so their URLs are never marked as scraped. The two multiply into tens of millions of Gemini prompt tokens per month, most of it wasted:

- **Bluebird**: 280 flash+screenshot calls over 32 daily runs; each call sends ~453–490 KB of HTML (~115–125k tokens) + a full-page screenshot; the same product is extracted exactly 3× per run (once per store page) and never persists. Est. **~40–50M tokens/month**.
- **Terarosa**: 286 flash+screenshot calls; active runs burn ~36 calls **on two non-coffee items** (a shopping bag and gift packing) that get AI-extracted and then rejected; est. **~19–25M tokens/month**, >95% junk.

## Method / log anatomy

Each scraper run is delimited by `🔄 Starting <name>` lines. Per AI call the log records `Using image analysis (<media>) for <url> (attempt N)` and `AI extracted successfully on attempt N: <name> from <origins>`. Failed generations embed Gemini `usage_metadata` with `prompt_token_count=` (e.g. a single **278,045-token** HTML-only call for another roaster). Live page sizes were measured with `curl_cffi` (`impersonate="chrome"`); persistence was cross-checked against `data/roasters/<roaster>/`.

## Bluebird Coffee Roastery (`bluebird_coffee.py`)

**Config**: `use_playwright=True`, `use_optimized_mode=True` → every attempt is `gemini-2.5-flash` + screenshot. No `preprocess_product_soup` / `_extract_bean_with_ai` override → the full WooCommerce page goes to the model.

**Per-call payload** (measured on live pages):
- HTML: 453–490 KB → ~115–125k text tokens (Gemini HTML tokenization is denser than prose; this is a floor).
- Full-page PNG screenshot: `BaseScraper.take_screenshot(full_page=True)`; Gemini bills images at ~258 tokens per 384×384 tile, so a tall 1280×N px screenshot is tens of thousands of tokens by itself.

**The multiplier — same product, 3 store pages, every day**:
- 21 of 31 runs show `calls = 3 × unique products` (e.g. `inmaculada-fellow-farms-geisha-2/` extracted on `product-tag/single-origin/`, `special-releases/` and `product-tag/espresso-blend/` → 9 identical flash+screenshot calls, `unique=1`).
- `_scrape_new_products` feeds the same new-product URL list to every store URL; a URL is only skipped once `_mark_bean_as_scraped` runs, i.e. only after a bean is saved.
- **The bean is never saved**: `data/roasters/bluebird_coffee_roastery/20260711…20260810` contain **only `.diffjson` stock files — zero bean `.json` files**, and `find … *inmaculada*` matches nothing, yet "AI extracted successfully" is logged every time with no ERROR line. The extraction result is silently dropped after the AI step, so the URL is re-extracted next page, next run.
- "Loaded N existing beans from all sessions" crept only 55 → 62 over 30+ runs — nearly every run's extraction work produced nothing.

**Result**: ~9–12 calls/run × ~160k tokens ≈ **~1.6M tokens per run; ~50M over the logged month**.

## Bluebird soup pruning — implemented & verified (2026-08-10)

### Page anatomy (live pages, parsed with bs4)

Bluebird product pages are OceanWP/WooCommerce rendered through an Elementor
product template (`div.elementor-location-single.product`), ~440–490 KB raw.
Every product shares an identical 8-section layout (verified on 4 live pages):

| # | Size | Content | Product-specific? |
|---|---|---|---|
| 0 | ~33 KB | breadcrumb, country, title, process, price range (e.g. `R 219.00 – R 806.00`), tasting notes, bag-size `<select>` (100g/250g/1kg), beans-or-ground `<select>`, quantity, Add to cart | ✅ |
| 1 | ~12.5 KB | spec table: Origin / Variety / Region / Producer / Altitude / Processing | ✅ |
| 2 | 3–5 KB | "Coffee Origins" description prose | ✅ |
| 3 | 3.3 KB | brew Recipe | ❌ static (identical every page) |
| 4–6 | ~9 KB | "Coffee at its best" / FAQs / "Subscribe, and save" | ❌ static |
| 7 | **99–100 KB** | "More coffees you may enjoy" — full cards (title, price, tasting notes, bag/grind options) of **other** products | ❌ noise |

The `<head>` is another ~152 KB of styles/scripts/JSON-LD with **no
machine-readable product data** (no `og:price:currency`, no
`Shopify.currency`; currency correctly falls back to the registry default,
ZAR). Stored beans were cross-checked against the page: the spec table and
price range match the saved `*.json` values exactly.

### Implementation (`src/kissaten/scrapers/bluebird_coffee.py`)

Four additions (ruff-clean, registry import verified, unit tests in
`tests/unit/test_bluebird_scraper_soup.py` — 4 pass):

- `_extract_bean_with_ai` override — prunes the soup before the shared flow
  serializes it (`str(soup)` is what actually goes to the model).
- `preprocess_product_soup` — keeps the Elementor product-specific sections
  (0–2), with fallbacks: generic WooCommerce `div.product` → summary/tabs
  containers, then full page if no product container exists (theme change →
  no silent data loss).
- `_is_boilerplate_section` — recognises the recipe / "Coffee at its best" /
  FAQ / "Subscribe, and save" / related-carousel sections by text markers.
- `_prune_soup_for_ai` — strips scripts/styles/svg/hidden containers, form
  inputs, collapses images to alt text, clears Elementor `data-*`/`class`
  attribute noise, collapses empty wrappers. Unlike the Shopify scrapers,
  **buttons, labels and variation `<select>`s are kept** — they carry the
  availability and weight/grind facts (Bluebird injects no JSON variant data).

### Measured effect (4 live pages)

| Page | Full HTML | Pruned | Reduction |
|---|---|---|---|
| inmaculada-fellow-farms-geisha-2 | 444 KB | 5.9 KB | 1.3% |
| finca-soledad-tyoxi | 440 KB | 3.9 KB | 0.9% |
| burundi-migoti-hill-honey | 444 KB | 5.0 KB | 1.1% |
| las-margaritas-red-bourbon | 443 KB | 4.5 KB | 1.0% |

Per call: **~1.3k HTML tokens vs ~111–125k before (~75× fewer)**. All bean
facts verified retained (title, price, tasting notes, spec table, bag/grind
options, "Add to cart" availability cue).

### Extraction comparison vs stored `*.json` (2026-08-10)

Live re-extraction of `burundi-migoti-hill-honey` with the new code, compared
to `data/roasters/bluebird_coffee_roastery/20260805/migoti_hill_honey_honey_170359.json`:

- **(c) pruned + optimized mode (production config: gemini-2.5-flash +
  screenshot)**: **matches the stored JSON on every meaningful field** —
  name "Migoti Hill Honey", country BI, region Bujumbura-Rural Province,
  producer Migoti Coffee Co., elevation 1750, process Honey, variety Red
  Bourbon, roast_profile Omni, price 219/250g ZAR, price_options
  (250→219, 1000→**806**), tasting notes [Golden Delicious Apple, Clementine],
  in_stock true, single_origin true. Description differs only because the
  page text itself changed since 08-05 (page drift, not pruning loss).
- **(a) full-page control, flash-lite HTML-only**: got the **1 kg price
  wrong (R399 vs the real R806)** — the full page's related-products
  carousel (other products' prices) actively misled the model. The pruned
  page (b) got it right. More HTML ≠ better extraction.
- Both flash-lite HTML-only runs missed the spec-table details
  (region/variety/elevation) — the known standard-mode weakness, present
  with the full page too (pre-existing, not a pruning regression).
- **Pre-existing quirk to watch**: standard mode returned `currency: GBP`
  for both full and pruned HTML despite the "Product Currency: ZAR" prompt
  anchor; optimized mode returns ZAR correctly. If Bluebird ever switches
  to standard mode, currency handling needs attention first (a GBP tag
  would corrupt `price_usd`).
- Nothing was written to `data/` during verification; extraction path only
  logs (logfire spans confirmed the models used: flash-lite vs flash).

### Still open for Bluebird

- **Never-save / re-scrape loop**: recent sessions contain zero bean
  `.json` files while "AI extracted successfully" is logged — the bean is
  dropped after the AI step, so URLs are never marked scraped and every run
  re-extracts the same products 3× (3 store pages). This is the bigger
  multiplier and remains unaddressed.
- **`use_optimized_mode=True` still sends the full-page screenshot** (~40k
  image tokens/call) — the other per-call cost lever, unchanged.

## Terarosa (`terarosa.py`)

**Config**: `use_playwright=True`, `use_optimized_mode=True`, `translate_to_english=True`. No soup pruning; full ~140 KB detail page (~35k tokens) + screenshot per call.

**The junk loop**:
- The category grid is scraped via `#itemList a[data-key]` with **no non-coffee filtering and no cross-category dedup**. Gift items appear in the grid, so every active run AI-extracts the same two non-coffee products:
  - `https://www.terarosa.com/product/detail/?ItemCode=100070` — "Terarosa Shopping Bag" (89 extractions)
  - `ItemCode=100363` — "Terarosa Gift Packing" / "[Terarosa X Oxford] Gangneung Main Branch Block"
- These extract fine ("AI extracted successfully on attempt 1") but carry no origins → base `_extract_bean_with_ai` returns None → `Failed to extract data from <url>` → URL never marked scraped → re-extracted on **every category store page** (6 categories) and every run (~36 calls/run).
- ~21 of 30 runs fail even earlier (homepage/category fetch flaky via Playwright → 0 product URLs → "No beans found"), which burns little AI budget but wastes a launch slot every run.

**Result**: ~36 calls/run × ~60–75k tokens ≈ **~2.2M tokens per active run; ~19–25M over the logged month, >95% on two junk products.**

## Terarosa fixes — implemented & verified (2026-08-10)

### Page anatomy (live pages, parsed with bs4 + Playwright)

Terarosa detail pages are server-rendered (`div.wrap > div.cont_wrap.product_view_wrap
> div.product_view > div.product_view_box`). Measured on 4 live pages
(2 coffees, the bag, the gift block):

- **`div.product_view_box`** (~27 KB of the ~137 KB page) is the product card:
  Korean/English title, tasting tagline, price/weight ("250g 29,500원, 1kg 93,000원"),
  grind/weight `<select>`s, roast date, and the product-photo carousel.
- The page is **17,454px tall and `div.product_view_cont` (상품정보 detail tab) is
  15,615px of it — a wall of long spec-sheet images** rendered `loading="lazy"`.
- **The origin spec sheet (country/region/farm/altitude/process/variety) is an
  IMAGE, not text**: 산지/가공/고도/품종 appear 0× in the static HTML and the
  detail container is empty until JS fills it with pictures. That is *why*
  Terarosa needs optimized mode + the full-page screenshot — flash-lite HTML-only
  cannot read origins from markup (see the comparison below).
- Everything outside the product card is boilerplate: header nav (~29 KB),
  review/purchase widgets (`product_view_cont_reivew` ~12 KB), the empty AJAX
  detail container, recommended carousels, chat/social scripts (~20 KB Kakao),
  footer.

### Implementation (`src/kissaten/scrapers/terarosa.py`)

Five additions (ruff-clean; 6 unit tests in
`tests/unit/test_terarosa_scraper_soup.py`; registry/import verified):

- `_extract_bean_with_ai` override — prunes the soup before the shared flow
  serializes it (currency detection and the rest are untouched).
- `preprocess_product_soup` — keeps `div.product_view_box`, drops
  review/tab/AJAX/pagination/breadcrumb boilerplate; falls back to
  `div.product_view` → `div.product_view_wrap` → full page (no silent loss).
- `_prune_soup_for_ai` — strips scripts/styles/attrs/hidden/inputs, collapses
  empties, and **keeps the product `<img>`s** (with a lift-out to work around
  lxml nesting `<img>` inside `<source>`) — the spec sheets must survive, and
  the photos double as the `image_url` source.
- `_is_non_coffee_accessory` + a rewritten `_extract_product_urls_from_store` —
  reads each grid item's Korean/English name and drops accessories **at
  discovery** (see "junk filter" below).
- `take_screenshot` override — fixes the cut-off full-page screenshot (below).

### Measured effect

| Page | Full HTML | Pruned | Reduction |
|---|---|---|---|
| ethiopia aricha (100499) | 139.7 KB | 4.7 KB | 3.4% |
| indonesia ribang gayo (100517) | 138.8 KB | 4.3 KB | 3.1% |
| shopping bag (100070) | 136.2 KB | 3.9 KB | 2.8% |
| oxford block (100363) | 137.4 KB | 4.1 KB | 3.0% |

Per call: **~1.2k HTML tokens vs ~31–35k before**, all bean facts retained
(title, tasting notes, price, weight/grind options, roast date, all photos).

### Junk filter (kill switch for the 36-calls/run loop)

Rendered root cause: **the shopping bag `100070` appears in all 6 category
grids** (the site injects it as "related" merchandise on every category page)
and the Oxford block `100363` in the drip-bag category — so every run
AI-extracted them on every category and rejected them for missing origins.

Fix: `_is_non_coffee_accessory(name)` drops grid items whose name has an
accessory keyword (쇼핑백/선물/포장/상자/틴케이스/아이스크림/블록 + bag/gift/wrap/box/
block/oxford/ice-cream/tin) **and no coffee keyword** (드립백/커피/원두/블렌드 +
coffee/bean/blend/drip/espresso). The coffee guard matters: the drip-bag set
`100315` ("드립백 20개입 & 옥스포드 블록 세트") is kept despite mentioning 블록.

Verified on all 6 live category grids (Playwright-rendered): the bag is dropped
from all 5 categories that contain it, the block from category 74, `100315`
kept → **34 unique coffee codes, zero junk**.

### Screenshot fix (page was cut off below the fold)

Base `take_screenshot` waits 2s and captures without scrolling, so the lazy
spec-sheet images 1,200–16,800px down the page never load on the server and the
full-page PNG came out **blank from the product-info section down** — the model
couldn't read the origin sheets. Override (same fix as `pala_kaffebrenneri`,
hardened for slow networks): scroll the page in 700px steps to trigger
`loading="lazy"` fetches, `wait_for_function` until all `document.images` are
`complete` (15s timeout), scroll back, then capture `full_page=True`.

### Extraction comparison vs stored `*.json` (2026-08-10, live)

Re-extraction of `100499` (ethiopia aricha) with the new code:

- **(c) pruned + optimized (production config)**: matches the stored
  `20260802/ethiopia_yirgacheffe_aricha_heirloom_washed_washed_004121.json`
  field-for-field — name, ET / Gedeo-Aricha, 1950 masl, Washed / Heirloom,
  harvest 2025-11-01, 29500 KRW, price_options (250→29500, 1000→93000),
  tasting notes (Orange, Coffee Blossom, Sweet, Fragrant Finish), roast
  Medium-Light / Omni, in_stock.
- **(a) full-HTML flash-lite control**: **hallucinated** — price 7.5 GBP
  (real: 29500 KRW), elevation 0, empty tasting notes. HTML-only cannot read
  image-based origins → **Terarosa must stay in optimized mode**; the pruner
  slimmed the prose payload while the screenshot carries the facts.
- **(b) pruned flash-lite**: rejected ("no origins") — same reason.

Full end-to-end rerun (2026-08-10, logfire spans `agent_full` flash+screenshot
→ translation pass) saved a bean into a timestamped session dir; compared
1:1 with the stored 08-02 file it matched on every field above, including the
harvest date and exact "Gedeo, Aricha" region.

## Root causes (ranked)

1. **Optimized mode everywhere** — both scrapers set `use_optimized_mode=True`, so every attempt is `gemini-2.5-flash` + full-page screenshot; there is no cheap `flash-lite` HTML-only first pass (standard mode does attempts 1–2 HTML-only on flash-lite).
2. **No HTML minimization** — 140–490 KB pages sent verbatim. Compare: redemption now prunes to ~16 KB; watchhouse / indigo / colonna all trim to a focused container before extraction.
3. **Failed/rejected beans are never marked scraped** — the URL re-enters `new_product_urls` on every overlapping store page (Bluebird ×3, Terarosa ×6 categories) and re-runs daily, multiplying the per-call cost ~3–6× and making the waste recur forever.
4. **Terarosa lacks URL-level non-coffee filtering** (bags/gifts) and URL dedup across categories.

## Recommended fixes & status

- ✅ **Bluebird soup pruning (implemented 2026-08-10)** — `preprocess_product_soup` keeps only the product-specific Elementor sections (0–2); ~440–490 KB → ~4–6 KB per call, verified against stored `*.json` (matches field-for-field in production config). See section above.
- ✅ **Terarosa soup pruning (implemented 2026-08-10)** — `preprocess_product_soup` keeps `div.product_view_box`; ~137 KB → ~4 KB per call, all text facts + product photos retained. See "Terarosa fixes" section above.
- ✅ **Terarosa junk filter (implemented 2026-08-10)** — bag `100070` (present on all 6 category grids) and Oxford block `100363` are dropped by name at discovery time; drip-bag + block set `100315` kept. Verified live: 34 unique coffee codes, zero junk.
- ✅ **Terarosa screenshot fix (implemented 2026-08-10)** — scroll-through + wait-for-images before the full-page capture; the lazy spec-sheet wall (15,615px) was blank in server captures. Same fix as `pala_kaffebrenneri`.
- ⬜ **Bluebird never-save / re-scrape loop (open)** — dedup the new-product URL list once across all store pages (not per store page) and fix the silent never-save path — a "successful" extraction whose bean fails validation should still be marked done for the session so it is not re-attempted 3× per run.
- ⬜ **Bluebird `use_optimized_mode` (open)** — consider flash-lite HTML-only first, escalate to screenshot only if needed; fix standard-mode currency detection ("GBP" quirk) before any switch.
- ⬜ **Terarosa run reliability (open)** — ≈21 of 30 logged runs die before any AI call ("No beans found" when the Playwright homepage/category fetch fails); wasted launch slots. Standard mode is **not** an option for Terarosa (origins are image-based) — instead consider retrying the store-URL discovery and/or running category fetches directly.
- ⬜ **General (open)** — in `scrape_with_ai_extraction`, dedup `new_product_urls` and skip URLs already attempted-and-failed in the current session.

## Related prior art

- The July analysis already flagged half of this: "Wasteful / duplicate AI extraction — Bluebird `inmaculada-fellow-farms-geisha-2` extracted ~6×" in [Scraper Log Analysis — July 2026](scraper-log-analysis-2026-07.md) (item #11).
- Redemption's soup pruning (power_section + `div.product`, plus markup/chrome stripping → 484 KB → 16 KB) is the working reference for fix #1.
