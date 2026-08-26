---
type: "Reference"
title: "MOK Coffee — Roaster Profile"
description: "Brussels specialty roaster whose coffee collection is scraped from a JavaScript-rendered Shopify catalogue."
---

# MOK Coffee — Roaster Profile

## Overview

MOK Coffee is a specialty coffee roaster based in Brussels, Belgium. Its registered storefront is Shopify and its coffee collection is `/collections/coffee`. The official storefront was rate-limited during this research pass, so further claims about its founding, address, sourcing, equipment, sustainability, or fulfilment are omitted rather than inferred.

## Address

- Brussels, Belgium — full roastery address not published on the pages available during this research pass.

## Scraping Quirks

- The registry key is `mok-coffee`. The scraper uses Playwright for the collection, selects only `a.product` links containing `/products/`, and excludes URLs containing `xmas` or `voucher`. It does not use a general product-link selector, so a future theme change could make the collection appear empty.

## Sources

- https://mokcoffee.be
- https://mokcoffee.be/collections/coffee
