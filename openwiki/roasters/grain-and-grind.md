---
type: "Reference"
title: "Grain and Grind — Roaster Profile"
description: "Scottish roastery near Inverness (with coffee shops across Glasgow & Inverness) on WooCommerce — 'The Best Small Batch Coffee' with ~30 coffee products and free delivery over £8."
---

# Grain and Grind — Roaster Profile

## Overview

Grain and Grind is a Scottish coffee roastery near Inverness, with coffee
shops across Glasgow and Inverness, on a WordPress WooCommerce storefront at
grainandgrind.co.uk. Its `coffee` product category carries ~30 products priced
in GBP at roughly £7.50–£9.50 a bag — single origins such as Brazilian Santos,
Colombian El Eden/Excelso/Rich Roast, Ethiopian Djimma/Limu/Yirgacheffe and
Costa Rica San Rafael, plus blends including Culloden Blend, Black Forest
Roast, Bungo Roast and Around The World, alongside Kenya/Uganda/Zambia lots.

## Address

- Scotland — United Kingdom (roastery near Inverness; coffee shops across
  Glasgow and Inverness — full street address not published on the site).

## Schedules & Shipping

- Free Delivery on all orders over £8.

## Philosophy & Quirks

- Self-described "The Best Small Batch Coffee" (site title).
- Culloden Blend — a nod to the Highland namesake.
- Region-focused single origins plus blends; subscriptions, brew bags and
  equipment are sold separately.

## Scraping Quirks

- WooCommerce (no products.json) — coffee lives in
  `/product-category/coffee/`, which is paginated and traversed via
  `a.next.page-numbers` (currently 3 pages / ~30 products).
- Sold-out items are detected by the `outofstock`/`sold-out`/`oos` CSS class
  on the `li.product` card before URL filtering.
- Product pages are compacted to the `div.product` container for AI token
  savings.
- Equipment, brew bags, merch and subscriptions live in separate categories
  that are never crawled; currency is pinned to GBP.

## Sources

- https://grainandgrind.co.uk
- https://grainandgrind.co.uk/product-category/coffee/