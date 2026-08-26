---
type: "Reference"
title: "Zennor Coffee — Roaster Profile"
description: "Glasgow-based specialty coffee roaster (roastery in Dennistoun, cafés in the Southside and on Duke Street) — despite the Cornish-village name — roasting single origins and house blends, with the sold-out Finca Anaya only in /collections/all."
---

# Zennor Coffee — Roaster Profile

## Overview

Zennor Coffee (zennorcoffee.co.uk) is a Glasgow-based specialty coffee roaster
(roastery in Dennistoun; cafés in the Southside and on Duke Street) — the
"Zennor" name echoes a Cornish village but the business is Glasgow-born. The
Shopify storefront sells a curated line-up of Ethiopian, Peruvian, Colombian,
Costa Rican, Panamanian and decaf coffees organised as Core Collection, Seasonal
Micro Lots and Rare & Limited, alongside loose-leaf teas and brewing equipment,
with free delivery over £30.

## Address

- Roastery in Dennistoun, Glasgow — full roastery street address not published
  on site (the site publishes only its café addresses). United Kingdom.

## Schedules & Shipping

- Free delivery on orders over £30 (storefront banner).

## Scraping Quirks

- No single curated "all coffee" collection holds every bean: the `coffee`
  (Core), `rare` (Rare & Limited) and `seasonal-lots` collections cover the
  live beans but miss the sold-out product. The scraper reads
  `/collections/all` and filters on `product_type == "Coffee"` — exactly 12
  beans (11 purchasable + the sold-out Finca Anaya, `in_stock=False`) with the
  filters/brewers that share the collection dropped.
- Despite the Cornish-village name, the business is Glasgow-based (roastery in
  Dennistoun, café in the Southside).
- The edge rejects curl_cffi's default libcurl TLS fingerprint (403 on
  products.json) — the scraper rebuilds its client with `impersonate="chrome"`
  (mirrors twoday.py).

## Sources

- https://zennorcoffee.co.uk
- https://zennorcoffee.co.uk/pages/354-duke-st
- https://zennorcoffee.co.uk/pages/287-langside-rd