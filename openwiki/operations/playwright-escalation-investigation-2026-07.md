# Playwright 429 Escalation Investigation — 2026-07-30

## TL;DR

The httpx → Playwright escalation introduced after the original analysis
**works** for the product-page fetch path in `BaseScraper.fetch_page_with_screenshot`
but is broken / ineffective in `ShopifyJsonScraper._fetch_all_shopify_products`:

1. **Bug 1 — wasteful retries before escalation**: Shopify scraper does 4 httpx
   attempts with 5/10/20s backoff (35s wasted) before escalating, vs the base
   class which escalates on the first 429 with 5s backoff.
2. **Bug 2 — no retries inside Playwright**: Shopify scraper attempts Playwright
   exactly once, even though it could be a transient throttle.
3. **Bug 3 — control-flow bug (latent)**: After escalation sets `data` from the
   Playwright HTML, control falls through to `response.raise_for_status()` and
   `data = response.json()` on lines 123-124 of `shopify_base.py`, which would
   `UnboundLocalError` on a future Playwright success.
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
