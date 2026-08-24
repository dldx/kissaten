---
type: "Reference"
title: "The Forge Coffee Roasters — Roaster Profile"
description: "Sheffield roaster on Squarespace (Brine) at forgecoffeeroasters.co.uk with a blend-led lineup (Invicta, Ruskin, Kropp) plus single origins in 250g/500g, roasted on a Giesen."
---

# The Forge Coffee Roasters — Roaster Profile

## Overview

The Forge Coffee Roasters is a Sheffield roaster on a Squarespace (Brine) storefront at forgecoffeeroasters.co.uk. The /store carries 6 coffee products in GBP — blends (Invicta/Ruskin/Kropp historically, Trinity Decaffeinated) plus single origins Brazil Sitio Da Torre (sold out), Guatemala Las Moritas £14.50, Rwanda KCRS Women's Co-op £10.50, Colombia Popayan Decaf and Luis Aníbal Calderón — in 250g/500g.

## Address

- Don Road, Sheffield, South Yorkshire S9 2TF — United Kingdom

## Philosophy & Quirks

- Roasts on a Giesen roaster; offers wholesale/consultancy and equipment servicing.
- Blend-led lineup (Invicta, Ruskin, Kropp) alongside single origins.

## Scraping Quirks

- The listed domain forgecoffeeroasters.com was drop-caught by HugeDomains (for sale, connection times out) — the real store is forgecoffeeroasters.co.uk (Squarespace).
- Product pages are at `/store/p/<slug>` (the Brine listing server-renders `div.product-list-item a[href*='/store/p/']` with unquoted hrefs).
- Sold-out beans are kept in the catalogue (out-of-stock diffs).
- Blends Invicta/Ruskin/Kropp currently 404 (removed from catalogue) — only their stale cards remain; the scraper URL-filters so only live products are fetched.
- Cups/equipment/accessories are excluded (22 non-bean items on the listing vs 6 coffee).
- Playwright screenshots may return None on networkidle hang → HTML-only fallback (0 errors). Currency is pinned to GBP.

## Sources

- https://www.forgecoffeeroasters.co.uk
- https://www.forgecoffeeroasters.co.uk/store