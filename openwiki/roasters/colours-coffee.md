---
type: "Reference"
title: "Colours Coffee — Roaster Profile"
description: "UK specialty coffee roaster (Instagram @colourscoffeeco) roasted in Wiltshire on a Shopify storefront, making complex specialty brews approachable through a curated 11-bean catalogue."
---

# Colours Coffee — Roaster Profile

## Overview

Colours Coffee (colourscoffee.com) is a UK specialty coffee roaster that
rebranded and moved from the now-dead colourscoffee.co.uk to this Shopify
storefront. Per the site copy, it roasts in Wiltshire and its mission is to
make complex specialty brews approachable for everyday coffee lovers. The
catalogue is a small, curated, rotating range of single origins, blends and a
decaf — all medium roast in this season — priced in GBP.

## Address

- Full street address not published on site — Wiltshire, England, United
  Kingdom.

## Scraping Quirks

- Domain correction: colourscoffee.co.uk → colourscoffee.com (old domain dead).
- Shopify using the curated `beans` collection, not `collections/all`, which
  mixes in 10 equipment/merch products (Aeropress, filters, grinders, cups,
  caps).
- Canonical product URLs are the no-collection `/products/<handle>` form; the
  collection segment is stripped to keep dedup aligned.
- The only exclusion is the `subscription-box` product; no tasting kits in the
  current bean line-up, so no kit-flagging needed.

## Sources

- https://colourscoffee.com
- https://colourscoffee.com/collections/beans/products.json
- https://colourscoffee.com/pages/faq