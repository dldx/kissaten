---
type: "Reference"
title: "Playwright 429 Escalation Investigation — 2026-07-30"
openwiki_generated: true
---

# Playwright 429 Escalation Investigation — 2026-07-30

> **Status (2026-07-31)**: Bugs 1, 2, 3, and 4 are **fixed** in
> `src/kissaten/scrapers/shopify_base.py`. The new ladder (one httpx attempt
> with 5s backoff, then up to `max_retries` Playwright attempts with 5/10s
> backoff, with escalation tracked *per page* instead of as an instance flag)
> is covered by 4 regression tests in `tests/unit/test_shopify_scraper.py`
> (`TestShopify429Escalation`). Live smoke tests against Caravan Coffee and
> Mirra Coffee from this laptop returned **11 and 21 products respectively** in
> ~10s, with a single httpx 429 → single Playwright call each — vs. the
> previous ~35s of wasted backoff and an empty result. See "Resolution
> (2026-07-31)" at the bottom of this doc.
>
> The original root-cause analysis below is preserved for historical accuracy.
> **Bug 3** (control-flow / fall-through) was re-characterised during the fix:
> the latent failure mode is not an `UnboundLocalError` (lines 123-124 live
> inside the `else:` block, so they're never reached when `_force_playwright`
> is True), but rather a successful Playwright parse being *discarded* by
> `response.raise_for_status()` on the leftover 429 response from line 95.
>
> **Bug 5** (HTML-collection-page fallback) is **YAGNI for the current
> proxy/throttle combination**: a live probe from this laptop showed Playwright
> succeeding against the same `products.json` URLs that bare `httpx` was
> being 429'd on. The throttle is fingerprint-shaped (bare httpx request), not
> IP-shaped, so the same proxy IP that gets bare-httpx-throttled lets
> Playwright through. Bug 5 may still be needed if a future proxy rotation
> removes the fingerprint gap, but it's not blocking any current scrapers.

## TL;DR

The httpx → Playwright escalation introduced after the original analysis
**works** for the product-page fetch path in `BaseScraper.fetch_page_with_screenshot`
but is broken / ineffective in `ShopifyJsonScraper._fetch_all_shopify_products`:

1. **Bug 1 — wasteful retries before escalation**: Shopify scraper does 4 httpx
   attempts with 5/10/20s backoff (35s wasted) before escalating, vs the base
   class which escalates on the first 429 with 5s backoff.
2. **Bug 2 — no retries inside Playwright**: Shopify scraper attempts Playwright
   exactly once, even though it could be a transient throttle.
3. **Bug 3 — successful Playwright data discarded on the escalation path**:
   After escalation, control falls through (within the same `else:` branch)
   to `response.raise_for_status()` on line 123 — where `response` is still
   bound to the **leftover 429 response from line 95**. That raises
   `HTTPError`, which the outer `except Exception` catches, and the
   successfully-parsed Playwright JSON is discarded. See "Bug 3 re-analysis"
   below for the correction to the original doc's `UnboundLocalError` claim.
4. **Architectural issue — same proxy backend**: Both httpx and Playwright use
   the proxy configured via `HTTP_PROXY`/`HTTPS_PROXY`, so when Shopify throttles
   the upstream IP at `/products.json`, Playwright gets the same 429. The
   escalation helps when the throttle clears within ~30s (Koppi, Workshop Coffee
   on 2026-07-30 succeeded) but fails for chronically throttled hosts (Coffee
   Sakura, Mazelab, Caravan, Calico, Nubra, Three Marks, Mirra, Cult, kaffaroastery,
   Sey, Alien Coffee — these hit "Failed after 3 retries" because Playwright
   also got 429).

The 2026-07-30 batch 1 still showed multiple Shopify scrapers failing through
the escalation. The #2 listing-fetch guard (issue #2 fix) correctly catches
the cascade: 82 skip-OOS log messages on the day, no data corruption.

---

## Empirical evidence

Sample of a successful base-class escalation on 2026-07-30 batch 1
(Workshop Coffee, lines 131163-131176):

```
04:04:51.842 INFO  HTTP Request: GET https://workshopcoffee.com/.../house-blends "429"
04:04:51.842 WARN  Received 429 from … via httpx. Upgrading request to Playwright
                     and retrying in 5.00s (attempt 1/3)...
04:05:02.602 INFO  Successfully fetched: https://workshopcoffee.com/.../house-blends
…
04:05:02.607 ✅ Success Workshop Coffee - 14 beans, 14 in stock
```

1 attempt, escalated after 5s, 14 beans found. **This path works.**

Sample of a broken Shopify-class escalation on 2026-07-30 batch 1
(Mirra Coffee, lines 131527-131551):

```
05:04:29.696 INFO  Fetching Shopify products: https://www.mirracoffee.com/products.json
05:04:29.696 INFO  HTTP Request: GET …/products.json "429"
05:04:29.696 WARN  Received 429 … Retrying in 5.00s (attempt 1/3)
05:04:34.704 INFO  HTTP Request: GET …/products.json "429"
05:04:34.704 WARN  Received 429 … Retrying in 10.00s (attempt 2/3)
05:04:44.728 INFO  HTTP Request: GET …/products.json "429"
05:04:44.728 WARN  Received 429 … Retrying in 20.00s (attempt 3/3)
05:05:04.749 INFO  HTTP Request: GET …/products.json "429"
05:05:04.749 ERROR Failed to fetch Shopify products from … after 3 retries via httpx
                     due to 429 Too Many Requests. Upgrading to Playwright.
05:05:04.749 INFO  Fetching Shopify products via Playwright: …
05:05:08.508 ERROR Failed to fetch Shopify products from … after 3 retries:
                     Client error '429 Too Many Requests'
…
05:05:08.508 ❌ Failed Mirra Coffee - No beans found
```

4 httpx attempts + 1 Playwright attempt = 35s wasted and no beans. **This path is broken.**

## Top Shopify endpoints escalated on the post-fix days

`grep -oP 'from \K[^ ]+' <log>` over all `Failed to fetch Shopify products … after 3 retries via httpx due to 429` lines, ranked:

| Endpoint | Times escalated & failed |
|---|---|
| `caffealiena.com/.../frontpage/products.json` | 5 |
| `seycoffee.com/.../coffee/products.json` | 4 |
| `nubra.coffee/en/collections/all/products.json` | 4 |
| `kaffaroastery.fi/en/.../kahvit/products.json` | 4 |
| `cultcoffeeroasters.com/products.json` | 4 |
| `caravanandco.com/.../new-coffee/products.json` | 4 |
| `44northcoffee.com/.../beans/products.json` | 4 |
| `zeffcoffee.com/.../all-products/products.json` | 3 |
| `threemarkscoffee.com/products.json` | 3 |
| `pomacoffee.com/.../all/products.json` | 3 |
| `shoebox.coffee/.../coffee/products.json` | 3 |
| `picolot.shop/products.json` | 3 |
| `mazelabcoffee.com/.../coffee/products.json` | 3 |
| `homegroundcoffeeroasters.com/.../coffees-specialty/products.json` | 3 |
| `driproasters.ch/.../coffee/products.json` | 3 |
| `decaf.at/en/products.json` | 3 |
| `cafeamorperfecto.com/.../cafes-de-caficultor/products.json` | 3 |

Each of these is a `ShopifyJsonScraper` subclass. The base-class
`fetch_page_with_screenshot` 429 path is reached for non-Shopify roasters
(`fluir.coffee`, `slowcoffee.co.nz`, `qimacafe.com`, etc.) and most of those
succeed via Playwright — confirming the architecture is the difference, not
the proxy by itself.

## Root cause

### `shopify_base.py` `_fetch_all_shopify_products` (lines 64-159)

The retry-then-escalate logic is shaped like this:

```python
for retry in range(self.max_retries + 1):              # 4 iterations (0,1,2,3)
    try:
        if self._force_playwright:                     # if escalated previously this session
            html_content = await self._fetch_with_playwright(url)
            data = json.loads(BeautifulSoup(html_content, "lxml").get_text(strip=True) or "{}")
        else:
            response = await self.client.get(url)
            if response.status_code == 429:
                if retry < self.max_retries:           # 3 httpx retries with 5/10/20s backoff
                    await asyncio.sleep(backoff_delay)
                    continue
                else:                                  # 4th iter: escalation
                    self._force_playwright = True
                    html_content = await self._fetch_with_playwright(url)
                    data = json.loads(...)
                    # ⚠️ falls through to:

        response.raise_for_status()                    # ⚠️ response is unbound
        data = response.json()                          # ⚠️ overwrites data
```

Three concrete failures:

1. **`max_retries=3` with full backoff before escalation** (35s wasted). The base
   class escalates on the first 429 with 5s backoff. Worth ~30s × ~140 escalations
   per day = 70 minutes of proxy-throttled time per day.
2. **Single Playwright attempt, no retry, no jitter.** The Playwright call is
   the same proxy backend and the same URL; if the throttle is still active we
   just lose the 1-3s it takes for Playwright to spin up.
3. **`response.raise_for_status()` on line 123 is dead code** that, when reached,
   raises `UnboundLocalError: local variable 'response' referenced before
   assignment`. This is masked today because the Playwright call itself raises
   first (which the outer `except Exception` swallows). If Playwright ever
   returns a 200 from a future proxy rotation / pool, the bug fires.

### Same-proxy problem

`BaseScraper._get_browser` (lines 232-280) reads `https_proxy` /
`http_proxy` env vars and passes them straight to Playwright. So an
upstream-IP-level rate limit on `/products.json` will hit Playwright too:

```python
proxy_url = self.https_proxy or self.http_proxy
…
launch_options["proxy"] = {
    "server": server_url,
    "username": parsed.username or "",
    "password": parsed.password or "",
}
```

When the day is calm and Shopify's per-endpoint throttle is intermittent,
Playwright usually wins (Workshop Coffee, Koppi). When the proxy is
chronically hot (Coffee Sakura, Mazelab, Caravan, Calico, Nubra, Three Marks,
Mirra) Playwright also returns 429 and the scraper ends with `❌ Failed`.

## Recommended fix (priority order, smallest first)

1. **Mirror base-class escalation in `_fetch_all_shopify_products`**: escalate
   on the first 429 with 5s backoff, do not loop through `max_retries` first
   (~30 LOC, fixes Wasteful Retries and No-Retry-Inside-Playwright).
2. **Add 1–2 retries inside the Playwright branch** (5/10s backoff, ~10 LOC).
3. **Fix the fall-through**: rewrap the inner block as
   `try: … finally: pass` and bind `data` only inside the success path
   (~5 LOC). Without this, a future fix that swallows the Playwright error
   would expose the UnboundLocalError on every successful escalation.
4. **Reset `_force_playwright = False` after a successful Playwright fetch**
   so the global flag doesn't poison other `products_json_urls` in the same
   session (~2 LOC). Today Caravan Coffee / 44 North / Nubra etc. all escalate
   on page 1 then keep using Playwright for page 2 even if page 1 came back
   healthy after the upgrade.
5. **HTML-collection-page fallback (architecture)**: when products.json fails
   permanently, fall back to fetching `/collections/<slug>` via Playwright and
   extracting product URLs from the rendered DOM. This dodges Shopify's
   per-endpoint throttle entirely since the HTML pages are a different
   endpoint and almost always succeed through the same proxy. Several of these
   scrapers also already have a non-trivial `_extract_product_urls_from_store`
   override (e.g. `mirra.py`) — the fallback hook fits cleanly.
6. **Per-host pacing** (separate work): a shared `asyncio.Lock` + last-fetch
   time keyed on hostname, with random 2-5s jitter. The original analysis
   flagged #5 as priority 5 in the suggested order; the cheapest version is a
   10-line lock around `self.client.get`.

## Suggested test plan

- Add a unit test that stubs `client.get` to return 429 four times in a row,
  asserts `_force_playwright` is set after the first attempt (not the fourth),
  and asserts the Playwright fetch is called twice with backoff.
- Add a regression test for the fall-through bug: stub Playwright to return
  valid HTML, ensure `data` is what `_fetch_with_playwright` produced, not
  whatever `response.json()` would have raised.
- Add a test that the post-fix Shopify scraper fetches the second
  `products_json_url` via httpx after a successful first-page Playwright
  upgrade (no global `_force_playwright` poisoning).

---

## Bug 3 re-analysis (2026-07-31)

The original doc claimed Bug 3 is an `UnboundLocalError` from `response`
being unbound at lines 123-124 when the Playwright branch sets `data`.
This was wrong. Looking at the indentation of the actual code:

```python
if self._force_playwright:                                       # 88
    html_content = await self._fetch_with_playwright(url)         # 92
    data = json.loads(...)                                        # 93
else:                                                             # 94
    response = await self.client.get(url)                         # 95
    if response.status_code == 429:                               # 97
        if retry < self.max_retries:                              # 98
            ...continue
        else:                                                     # 108
            self._force_playwright = True
            html_content = await self._fetch_with_playwright(url) # 118
            data = json.loads(...)                                # 119-121

    response.raise_for_status()                                   # 123 — inside else:
    data = response.json()                                        # 124 — inside else:

products = data.get("products", [])                               # 126
```

`response.raise_for_status()` and `data = response.json()` are at the same
indentation level as `if response.status_code == 429:` — i.e. they live
**inside the `else:` block**, not after it. So:

- When `_force_playwright = True` on entry: the if branch is taken, lines
  123-124 are not reached, the Playwright data flows to line 126 cleanly.
  No `UnboundLocalError`. This was confirmed empirically by a regression
  test (`test_subsequent_page_with_force_playwright_uses_pw`).
- When the **escalation** path (lines 108-121) sets `data` from Playwright:
  `response` is still bound to the 429 from line 95. Control reaches line
  123 → `response.raise_for_status()` raises `HTTPError` on the 429 → outer
  `except Exception` catches → listing marked as failed → return `[]`.

**The real latent bug**: the escalation path successfully fetches Playwright
HTML, parses it into `data`, and then immediately throws that data away by
running `raise_for_status()` on the leftover 429 from the prior httpx call.
Every successful Playwright parse was being discarded by code that has no
business being on the Playwright success path.

The fix in `_fetch_page_with_escalation` (`shopify_base.py:108-194`) splits
the success and failure paths cleanly: httpx bind-and-go, on 429 sleep 5s,
then Playwright in a separate loop with `data` bound only inside the success
path. There is no shared fall-through between the two.

---

## Live probe results (2026-07-31, from this laptop)

The user's `.env` has `HTTPS_PROXY` pointed at this IP, so a raw `httpx`
request from this machine sees exactly the same upstream throttle behavior
as the proxied scraper run in production. Probe script:
`/tmp/opencode/probe_shopify.py`. Results: `/tmp/opencode/probe_results.md`.

| Endpoint | httpx | httpx after 30s wait | Playwright (no proxy) |
|---|---|---|---|
| `mirracoffee.com/products.json` | **429** `local_rate_limited` (18B) | **429** `local_rate_limited` | **200**, 103KB valid Shopify JSON |
| `mirracoffee.com/collections/all` | **429** `local_rate_limited` | — | — |
| `mirracoffee.com/` | **429** `local_rate_limited` | — | — |
| `caravanandco.com/.../new-coffee/products.json` | **429** `local_rate_limited` | **429** `local_rate_limited` | **200**, 72KB valid Shopify JSON |
| `caravanandco.com/collections/new-coffee` | **429** `local_rate_limited` | — | — |

**Implication**: the throttle is **fingerprint-shaped**, not IP-shaped.
Bare `httpx` requests are 429'd on the proxy (18-byte `local_rate_limited`
response), but Playwright's browser fingerprint passes through cleanly on
the **same proxy IP**. The original doc's "same proxy → same 429"
architectural hypothesis does not hold here — at least not for the current
proxy configuration.

This means **Bug 5 (HTML-collection-page fallback) is YAGNI for the
scrapers profiled above**: Playwright already wins, so the only thing the
HTML fallback would buy is robustness if the proxy is rotated to a config
where Playwright also gets 429'd. Keep the ticket open for that case but
don't ship it preemptively.

---

## Resolution (2026-07-31)

Implemented: refactored `_fetch_all_shopify_products` into a two-step ladder
with per-page escalation tracking. The instance-level `_force_playwright`
flag is no longer used by the Shopify subclass — each page independently
tries httpx first, escalating to Playwright only on 429.

**Code changes**:

- `src/kissaten/scrapers/shopify_base.py:64-194` — new
  `_fetch_all_shopify_products` loop + `_fetch_page_with_escalation` helper.
- `tests/unit/test_shopify_scraper.py` — new `TestShopify429Escalation` class
  with 4 regression tests + 1 sanity test, plus
  `test_shopify_scraper_escalates_quickly_on_429` replacing the old
  `test_shopify_scraper_429_retry_limit` (which encoded the old buggy
  behavior).

**Behavior after the fix** (live smoke tests, `/tmp/opencode/smoke_shopify.py` and the production rerun script `scripts/rerun_failed_shopify_scrapers.sh`):

| Scraper | httpx calls | Playwright calls | Products fetched | Wall-clock |
|---|---|---|---|---|
| Caravan Coffee | 1 (was 4) | 1 (was 1) | **11** | **9.4s** (was 35s+) |
| Mirra Coffee | 1 (was 4) | 1 (was 1) | **21** | **11.0s** (was 35s+) |
| Watchhouse (rerun, 2026-07-31) | 1 (429) | 1 (200) | **1** (full session) | **~6s** (single 5s escalation backoff) |

Watchhouse was previously failing every day on the refresh retry path (it
wasn't in the chronic-offenders post-fix list because it succeeded in the
main seed run, but the retry path was hitting the same 429 ladder). The
2026-07-31 rerun via `scripts/rerun_failed_shopify_scrapers.sh --only
watchhouse` recovered cleanly on the first escalation cycle — single httpx
429, 5s backoff, single Playwright success. The log captured the exact
ladder path:

```
INFO:httpx:GET https://watchhouse.com/.../products.json?limit=250&page=1 "HTTP/1.1 429 Too Many Requests"
WARNING:Received 429 Too Many Requests from https://watchhouse.com/.../products.json via httpx. Upgrading to Playwright in 5.00s...
INFO:Fetching Shopify products via Playwright: https://watchhouse.com/.../products.json
```

Both scrapers transitioned from `❌ Failed - No beans found` (with the
listing marked as failed) to a successful products.json fetch with all
expected products extracted on the first call. No diffjson poisoning because
the listing-fetch guard still fires on the genuinely-failed cases (where
both httpx and Playwright fail).

**Remaining work** (not in this change):

- #5 (HTML-collection-page fallback): YAGNI based on probe evidence; reopen
  if a future proxy rotation removes the Playwright fingerprint gap.
- #6 (per-host pacing): still worth doing as a separate ticket. The probe
  evidence suggests the throttle is fingerprint-shaped, so per-host jitter
  is less load-bearing than originally estimated, but it would still reduce
  the rate of `429`s in the first place.
