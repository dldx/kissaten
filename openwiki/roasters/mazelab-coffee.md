---
type: "Reference"
title: "Mazelab Coffee — Roaster Profile"
description: "Prague specialty roaster whose Shopify coffee collection is enriched from a deliberately simplified product-page extract."
---

# Mazelab Coffee — Roaster Profile

## Overview

Mazelab Coffee is a specialty coffee roaster based in Prague, Czech Republic. The registered storefront is Shopify and its coffee collection is exposed through a collection-specific `products.json` endpoint. The official site returned a rate-limit response during this research pass; consequently, no unverified address, machine, sustainability, sourcing, or shipping details are asserted.

## Address

- Prague, Czech Republic — full roastery address not published on the pages available during this research pass.

## Scraping Quirks

- The registry key is `mazelab-coffee`. The Shopify scraper fetches product pages, caches them, and in `preprocess_product_soup` replaces the origin-map and coffee-about sections with plain text when both are present, reducing the HTML sent to the extractor. It does not use the optimised extraction mode.

## Sources

- https://mazelabcoffee.com
- https://mazelabcoffee.com/collections/coffee/products.json
