---
type: "Reference"
title: "Full Court Press Coffee Roasters — Roaster Profile"
description: "Bristol specialty roastery on Squarespace at fcp.coffee with ~42 coffee products — washed/filter single origins and espresso blends — in 200g/500g/1kg, GBP."
---

# Full Court Press Coffee Roasters — Roaster Profile

## Overview

Full Court Press is a Bristol specialty roastery on a Squarespace storefront at fcp.coffee. It carries ~42 coffee products — Ninga, La Tortuga, Shyira Anoxic, Finca Chelin Gesha, washed/filter single origins and espresso blends — in 200g/500g/1kg, GBP. It also sells brewing equipment and offers subscriptions.

## Address

- Bristol, England — United Kingdom (full street address not published on site)

## Philosophy & Quirks

- Filter-focussed roastery selling washed/filter single origins alongside espresso blends (per its site).

## Scraping Quirks

- Squarespace — the `/shop`→`/coffee` listing page only server-renders 13 of 44 products (the rest lazy-load), so the scraper seeds from `/sitemap.xml` (complete enumeration).
- Product pages are `/products/p/<slug>` (NOT the `/shop/p` form).
- Two `/products/p/` URLs are art prints ("Rosi Tooth" FCP posters) — keyword-excluded.
- `-filter` slugs (e.g. washed-burundi-yandaro-filter) are roast-style beans, correctly retained.
- Screenshots hit a networkidle timeout → HTML-only fallback (0 errors, 39/42 beans). Currency pinned to GBP.

## Sources

- https://www.fcp.coffee
- https://www.fcp.coffee/sitemap.xml