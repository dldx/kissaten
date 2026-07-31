# Scraper Log Analysis — July 2026 (Post-Fix)

Follow-up to `scraper-log-analysis-2026-07.md` after the deployed code improvements
(proxy rotation + `BaseScraper`/`ShopifyJsonScraper` listing-fetch guard + new
`validate-db` checks G/H). Analysis covers `logs/scrape.log` from 2026-07-10 through
the 2026-07-30 batch 15 tick (138,333 lines, file mtime 2026-07-30 19:07).

The original 2026-07-29 batch (line 122601) is where the configured proxy was
rotated to a new upstream; everything from that tick onward is "post-fix".
18 batches ran on 2026-07-30 alone, the most reliable signal we have.

---

## Status by original issue

| # | Issue | Status | Evidence |
|---|---|---|---|
| 1 | Proxy SPOF | ✅ Fixed | Proxy rotation at the start of 2026-07-29. Zero timed-out / unreachable-proxy events on the prior upstream seen on 2026-07-30. No Logfire export-retry storms after the swap. |
| 2 | Failed fetch wipes catalogue OOS | ✅ Fixed | 82 × `Skipped out-of-stock updates: listing fetch failed …` and 1 × `Refusing to mark all 12 known products out of stock: no current product URLs were found`. Café Amor Perfecto, Terraform, Nubra, Three Marks, Caravan, Mirra, Mazelab, Aila all correctly skip OOS updates on 2026-07-30 when `products.json` fails. |
| 3 | Proxy-UK currency corruption | ⚠️ Partial | Frequency down dramatically (5 GBP-detection calls on 2026-07-30 vs 265 across the whole log), but still 1 × `Overwriting bean currency with store currency: GBP` per post-fix run for roasters the proxy hits from the UK store page. |
| 4 | Persistent hard failures | ❌ Not fixed | Same chronic offenders: Extract 21d, Revel 21d, Skinny Dip 20d, Terarosa 20d, Ukkei 12d, Mazelab 12d, Naughty Dog 11d, Nubra 9d, Sey 8d — flat or slightly worse than the original analysis. |
| 5 | Shopify 429 rate-limiting | ⚠️ Partial | Playwright escalation wired (`Upgrading to Playwright (setting _force_playwright)`), but Playwright also fails with 429 because it shares the proxy. 612 × `429` on 2026-07-30 alone. Five scrapers (Coffee Sakura, Mazelab, Caravan, Calico, Nubra, Mirra) end up with `❌ Failed - No beans found` despite escalation. See "Investigation needed below". |
| 6 | `db_refresh` SIGKILL / exit 1 | ⚠️ Partial / worse | 23 × exit -9 (was 16) + 10 × exit 1 = 33 (was 26). Concentrated at end of window. |
| 7 | `validate-db` failed 12× silently | ✅ Fixed | All 12 failures are 2026-07-20 (lines 63493-68500). Zero validation failures across the 18 post-fix batches on 2026-07-30. 268 successful validation runs since 2026-07-20. |
| 8 | Native Coffee Company staging | — Not checked | |
| 9 | Suspicious mass OOS reported success | ⚠️ Partial | Helped indirectly via the #2 guard. Nubra still flags as "❌ Failed" on hard-listing-failure runs (skip path kicks in). |
| 10 | Puerto Blest / Fuego pagination double-count | ❌ Not fixed | 2026-07-30 Puerto Blest still issues `?mpage=2`, reports 26 stock updates for 13 unique products. No cross-page URL dedup. |
| 11 | Duplicate AI extraction | ❌ Not fixed | `inmaculada-fellow-farms-geisha-2` still extracted 175× across the log (9× on 2026-07-30). Slow Coffee `the-nz-team-blend` double-extract on 2026-07-30 batches. |
| 12 | Naughty Dog false failure | ✅ Fixed | 2026-07-29 / 2026-07-30 Naughty Dog: `✅ Success The Naughty Dog - 4 beans` / `- 2 beans` even when 0 in stock. |
| 13 | AI extraction fragility | — Stable | |
| 14 | Corrupt Tanat JSON | ❌ Not fixed | 21 occurrences (was 19). `data/roasters/tanat_coffee/20251021/liberica_champagne_…_010622.json` not quarantined. |
| 15 | 404s retried 3× | ⚠️ Partial | 12 × 404 on 2026-07-30 (down from 543 in the full log). Some scrapers now skip retries on permanent errors but not all. |
| 16 | Uncle Ben's selector timeout | ⚠️ Partial | 3 occurrences on 2026-07-30 (one per page × 1 run). Screenshot fallback still doing 30s waits per page. |
| 17 | Log noise | ❌ Not fixed | 1,719 × `Logfire project URL:` (~5/batch). Exclusion dedup missing on some roasters. |
| 18 | Recurring benign warnings | — Stable | |

**Score**: 4 fixed · 6 partial · 7 not fixed (plus 2 not re-checked).

---

## What's working

The two priorities from the original analysis are genuinely fixed and the
data-integrity risk they created is gone:

- **#1 (proxy SPOF)** — proxy rotation is the first thing any future outage
  should hit. Outage-era symptoms (`Connection to <upstream> timed out`,
  `Currently retrying N failed export(s)`) are absent from 2026-07-29 onward.
- **#2 (out-of-stock clobber)** — the failed-listing-fetch guard plus validate-db
  checks G/H prevent the worst failure mode. Even when every scraper in a batch
  fails (e.g. 2026-07-30 batches with 53.8%-69.2% success), no out-of-stock
  updates are written for the failed roasters.

## What's broken

- **#4 / #10 / #11** are the cheapest remaining wins.
- **#3 (currency)** still triggers once per day; pinning the roaster-configured
  currency is low-effort.
- **#5 (429 → Playwright)** is the open investigation; see below.

---

## Investigation needed: Playwright escalation

Several Shopify scrapers now log
`Failed to fetch Shopify products from <url> after 3 retries via httpx due to 429 Too Many Requests. Upgrading to Playwright (setting _force_playwright)`
on 2026-07-30:

- Coffee Sakura (`shop.coffeesakura.co.jp`)
- Mazelab Coffee (`mazelabcoffee.com`)
- Caravan Coffee (`caravanandco.com`)
- Calico Coffee (`calicocoffee.co.uk`)
- Nubra Coffee Roasters (`nubra.coffee`)
- Mirra Coffee (`www.mirracoffee.com`)

In every case Playwright also receives `429 Too Many Requests` because it routes
through the same proxy as httpx. The scraper then logs
`Failed to fetch Shopify products from <url> after 3 retries: Client error '429 Too Many Requests'`
and ends up with `❌ Failed - No beans found - Skipped out-of-stock updates: listing fetch failed`.
No beans are extracted for these roasters on those days.

This is the next investigation target.
