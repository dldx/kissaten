# Scraper Log Analysis — July 2026

Analysis of `logs/scrape.log` (~128k lines, covering **2026-07-10 → 2026-07-29**, all 16 daily batches).
Issues are ordered by severity. Each item is intended to be tackled one by one.

---

## Critical

### 1. Total scrape outage for ~2 days — proxy is a single point of failure

- **Window**: 2026-07-27 batch 2 → 2026-07-28 batch 16 — **31 consecutive batches** finished with 0/13 or 0/14 scrapers successful (~400 failed runs).
- **Root cause** (visible in log): `ProxyError('Unable to connect to proxy', ConnectTimeoutError(..., 'Connection to 51.9.121.235 timed out. (connect timeout=10)'))` — the single shared proxy died, taking down **all scraping and Logfire exports** (`WARNING:logfire:Currently retrying N failed export(s)` ×480).
- **Diagnosability problem**: per-scraper error messages are empty — `Request error: ` / `Error fetching <url>: . Retrying in 2.00s...` — the underlying exception `str()` is blank, so the failure is invisible unless you find the Logfire `UserWarning` far up the log.

### 2. Failed scrapes mark the entire catalogue out of stock — and validation passes anyway

> **Status (2026-07-30): fixed + cleanup in progress.**
> - Scraper guards: `BaseScraper`/`ShopifyJsonScraper` now track failed listing fetches per session and skip out-of-stock updates; a hard floor in `_create_out_of_stock_updates` refuses to wipe a whole catalogue from an empty product list.
> - validate-db: new checks G (in-stock drift vs snapshot) and H (last-batch health from `data/last_batch_results.json`) block promotion after mass failures/flips.
> - Cleanup: `scripts/quarantine_bogus_oos.py` quarantined 25,839 bogus `*_out_of_stock.diffjson` files to `quarantine/2026-07-cleanup/` (1,129 of them were the newest observation for their URL — DB repair + snapshot re-baseline still pending).
> - Tests: `tests/unit/test_out_of_stock_guard.py`, `tests/unit/test_validate_db_checks.py`.

- When a listing fetch fails, the scraper still runs `Creating out-of-stock updates for N products` for **every previously known bean** of that roaster.
- During the outage alone there were **~395 such events** — effectively the whole DB was flipped to out-of-stock by a network failure.
- `validate-db` **passed every single time** during the outage, so the poisoned rw DB was promoted to production. The volume-drift check does not catch mass in-stock→out-of-stock flips.
- Same failure mode at smaller scale for persistently blocked roasters (Revel, Extract, Ukkei): every daily run marks their whole catalogue out of stock because of a 403.

### 3. Currency detection is corrupted by the proxy's UK exit

- `Detected store currency from collection page: GBP` appears **120 times** — including stores that are clearly not GBP:
  - `roguewavecoffee.ca` (should be CAD, ×7)
  - `shop.coffeesakura.co.jp` (should be JPY, ×9)
  - `shop.apollons-gold.com` (should be JPY, ×5)
  - `axilcoffee.com.au` (should be AUD, ×5)
  - `www.seycoffee.com` (should be USD, ×12)
  - `rishcoffee.com` (×17), `chronic-coffee.co.uk` (×16), `cultcoffeeroasters.com` (×13)
- Shopify geolocalizes prices by visitor IP; the proxy exits in the UK; the scraper then logs `Overwriting bean currency with store currency: GBP`. Prices for CA/JP/AU/US roasters are stored as GBP, silently corrupting `price_usd` normalization.
- Only Loumi was caught (`Bean Burundi Kayanza Red Bourbon has unexpected currency GBP, expected UAH` → bean removed by postprocessing) because it has a roaster-specific currency guard.

---

## High

### 4. Persistent hard failures that never recover

| Roaster | Days failed | Error |
|---|---|---|
| Extract Coffee | 18 | HTTP 403 (bot protection) |
| Revel Coffee | 17 | HTTP 403 |
| Skinny Dip Coffee | 17 | No beans found |
| Terarosa | 16 | No beans found |
| The Naughty Dog | 11 | No beans found (false negative — see #12) |
| Mazelab Coffee | 10 | `Found 0 coffee product URLs out of 0 total products` |
| Ukkei | 9 | HTTP 403 |
| Sey Coffee | 7 | No beans found |
| Nubra Coffee Roasters | 7 | No beans found (see #9) |
| Kaffa Roastery | 7 | No beans found |
| Drip Roasters | 7 | No beans found |
| Aliena Coffee Roasters | 7 | No beans found |
| atmans, ZEFF., Rogue Wave, Passage, D Stands For, Coffee Wallas, Calico, Calendar, Café Amor Perfecto, Black & White, Archetype, 44 North | 6 each | No beans found |

- 403s are retried 3× via httpx with **no Playwright escalation**, then the scraper fails (and mass-marks out of stock per #2).

### 5. Widespread Shopify 429 rate-limiting through the shared proxy IP

- **2,531 ×** `429 Too Many Requests` in the log.
- Worst hit: **Café Aconcagua** (4 of 5 `products.json` collections exhausted all retries → only 2 beans left "in stock", 23 marked out of stock), **Acoustic Java** (2/3 collections lost), **kaffeemacher** (2/3), **Blue Bottle JP** (1/2).
- The 5/10/20s backoff does not help — the proxy IP itself is throttled, and collections are fetched back-to-back with no per-host pacing or jitter.
- Some scrapers escalate collection-page 429s to Playwright (works), but the `products.json` fetches in `shopify_base` do not.

### 6. `db_refresh` is unreliable

- **16 × killed with exit code -9** (SIGKILL — OOM or external timeout kill), including a near-unbroken streak at the end of the log (2026-07-29 batches).
- **10 × exit code 1** earlier in the window (e.g. 2026-07-10 batches 8 & 9).
- Consequence: many batches scraped fine but never refreshed the rw DB. The warning `(scraping results are still valid)` understates the impact — data freshness degrades silently.

### 7. `validate-db` failed 12 consecutive times on 2026-07-20

- Batches 1–12 of 2026-07-20 all ended with `❌ Validation FAILED (exit 1). Do NOT promote rw_kissaten.duckdb to production.`
- Good: promotion was correctly blocked. Bad: no alerting is visible; it failed silently all day and self-resolved.

---

## Medium / data quality

### 8. Native Coffee Company — staging domain + per-size SKUs + currency flapping

- Scrapes the raw myshopify staging domain `40c504-61.myshopify.com` instead of a branded domain.
- Products are per-size `*-inventory-tracking` SKUs (`kitsune-100g-inventory-tracking`, `aka-200g-...`).
- Repeated AI output-validation failures: `price: Input should be greater than 0 (input_value=0)`, `Price for 100g in USD must be between 1.00 and 250.00`.
- Detected currency **flaps between USD and GBP across retries of the same product** (symptom of #3).

### 9. Suspicious mass out-of-stock events reported as "success"

- **Nubra**: all 76 existing beans marked out of stock, only 4 product URLs found, reported `✅ Success — 19 beans` with 0 in stock. Likely collection/URL mismatch.
- **Picolot**: `✅ Success — 58 beans` with **0 in stock**.
- **Aery**: 8 beans found but only 1 in stock (50 marked out of stock).
- These look like catalog-structure changes, not real stock changes — needs a sanity threshold before mass out-of-stock marking is trusted (related to #2).

### 10. Pagination double-counting

- **Puerto Blest** and **Fuego Tostadores**: report 13 URLs on page 1 *and* the same 13 on `?mpage=2` → "26 beans, 26 in stock" from 13 unique products (26 stock updates for 13 existing beans). The store appears to ignore the page param; the scraper doesn't dedupe across pages.

### 11. Wasteful / duplicate AI extraction

- **Bluebird**: the same product URL (`inmaculada-fellow-farms-geisha-2`) extracted **~6×** across its three store pages; no cross-page URL dedup.
- **Slow Coffee**: same blend (`the-nz-team-blend`) extracted twice concurrently.
- Non-coffee items are sent to the AI and only dropped in postprocessing: barista course (Three Marks), t-shirts (Rish, People's Possession), gift card (Kafferäven), "Lucky Dip" (Outpost), "Mystery Can" / tattoo (People's Possession), APAX mineral concentrates (Nostos), drip bags (PLOT).

### 12. False failure classification — The Naughty Dog

- Did its job correctly (`Diffjson stock updates: 20 in stock, 69 out of stock`) but session ended `beans_found=0` → reported `❌ Failed - No beans found`. Diffjson-only scrapers that create no new beans are misclassified as failures.

### 13. AI extraction fragility

- Blends with `origin=None` fail postprocessing (H&S Sweetwater Blend, Double Diamond Dark).
- Gemini `503 UNAVAILABLE — high demand` bursts (People's Possession, Aery) — transient and retried OK, but each failure dumps a ~40-line traceback at WARNING.
- Pydantic output-validation failures (`Exceeded maximum retries (1)`) likewise log full tracebacks — expected-condition noise.

---

## Low / hygiene

### 14. Corrupt data file read every run

- `data/roasters/tanat_coffee/20251021/liberica_champagne_yeast_inoculated_anaerobic_natural_..._010622.json` — `Expecting value: line 55 column 3 (char 2792)`. Logged **19×** (once per run). Should be quarantined or repaired.

### 15. 404s retried 3×

- 96B (`smoke-drip-espresso-phin` → 301 → 404, retried 3×), Tanat pagination (`/page/5/` 404 retried 3×). Permanent errors shouldn't consume the retry budget.

### 16. Uncle Ben's selector broken

- `Could not find product-info element` (10s Playwright timeout) on all 3 collection pages every run — layout changed; screenshot fallback still works, but ~75s wasted per run.

### 17. Log noise

- Duplicate exclusion lines (Proud Mary logs the same subscription URL ~35× per run; exclusion dedup missing).
- `Logfire project URL: ...` printed 4× per batch (subprocess re-init).
- ~6.4k log lines/day makes real issues hard to spot.

### 18. Recurring benign warnings worth triaging

- `Currency not found in HTML meta tags or Shopify metadata` ×619 (non-Shopify scrapers rely on AI/page heuristics).
- `Excluding URL due to pattern` — top patterns: `subscription` (2721), `gift-card` (505), `shirt` (428), `origami` (349), `capsules` (248) — fine, but verify none over-match coffee products.
- Cartwheel: Playwright `Page.goto` screenshot timeout 30s (still succeeds).

---

## Suggested priority order

1. **#2** — Gate out-of-stock marking on a *successful* listing fetch; add a mass-stock-flip check to `validate-db`.
2. **#3** — Pin currency to the roaster's configured currency instead of proxy-geolocated detection.
3. **#1** — Proxy failover / monitoring / non-empty error messages.
4. **#6 / #7** — Make `db_refresh` SIGKILLs and `validate-db` failures alert loudly.
5. **#5** — Per-host pacing + Playwright escalation for `products.json` 429s.
6. **#4** — Per-roaster triage of the persistent-failure table.
7. **#9 / #10 / #12** — Scraper-specific correctness fixes.
8. **#11 / #13** — Dedup + pre-filter before AI extraction to cut token spend.
9. **#14–#17** — Hygiene.
