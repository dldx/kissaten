---
type: "Reference"
title: "Yellow Bourbon Coffee Roasters — Roaster Profile"
description: "Independent Northampton specialty coffee roaster on Angel Street in the Cultural Quarter, roasting in the back of the shop, with the Shopify storefront on yellowbourbon.net."
---

# Yellow Bourbon Coffee Roasters — Roaster Profile

## Overview

Yellow Bourbon Coffee Roasters is an independent specialty coffee roaster in
Northampton (Angel Street, in the Cultural Quarter), roasting in the back of
its shop and serving the beans there or selling them in bags for home. The
shop storefront is the yellowbourbon.net Shopify site; yellowbourbon.co.uk
remains a legacy/informational site whose shop links point to the .net store.
The curated `shop` collection carries ~7 whole-bean coffees — single origins,
house/espresso blends and a Swiss Water decaf, all Shopify-typed `Coffee`.

## Address

- Angel Street, Northampton, NN1 1ED — United Kingdom (in Northampton's
  Cultural Quarter; roasting happens in the back of the shop).

## Philosophy & Quirks

- "We select outstanding coffees from around the world, roast them in the back
  of the shop and serve them as drinks or in bags to use at home."
- Shop owner Steve has 8+ years of technical coffee experience, from roasting
  and QC through sourcing, brewing and training (per their site).

## Scraping Quirks

- Domain correction: yellowbourbon.co.uk is legacy/informational — the live
  shop is yellowbourbon.net, which rejects curl_cffi's default libcurl TLS
  fingerprint (403) so the scraper rebuilds its client with
  `impersonate="chrome"` (mirrors twoday.py).
- `collections.json` advertises an inflated count (51) for the curated `shop`
  collection; the real count is 7 `Coffee`-type products. The scraper prefers
  `collections/shop/products.json` over the 22-product `products.json` and
  filters on `product_type == "Coffee"`.

## Sources

- https://yellowbourbon.net
- https://www.yellowbourbon.co.uk/contact/
- https://www.yellowbourbon.co.uk/our-story/