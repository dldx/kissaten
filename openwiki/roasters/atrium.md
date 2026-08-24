---
type: "Reference"
title: "Atrium Coffee Roasters — Roaster Profile"
description: "Manchester specialty roaster on a WooCommerce/Divi storefront, organised into collections: coffee, single-origin, blends, espresso, decaf, a premium Gold Leaf Series, and a coffee Club."
---

# Atrium Coffee Roasters — Roaster Profile

## Overview

Atrium Coffee Roasters is a Manchester-based specialty roaster running a
WooCommerce/Divi storefront at
[atriumcoffeeroasters.com](https://atriumcoffeeroasters.com). (The checklist's
`atriumcoffee.co.uk` domain is dead.) We only verified the storefront itself —
no about/sustainability page has been confirmed yet — so this profile covers the
shop's structure and its scraping quirks only.

## Address

- Manchester — United Kingdom (full address not published on the site)

## Storefront Structure (verified)

- Organised into collections: **coffee**, **single-origin**, **blends**,
  **espresso**, **decaf**, and a premium line called the **Gold Leaf Series**
- Also sells a coffee **"Club"** (subscription) and **merchandise**

## Scraping Quirks

- The atelier's `/product-category/decaf/`, `blends`, `espresso` and
  `gold-leaf-series` archives render **without product cards server-side**, so
  crawling them trips the out-of-stock guard (an empty product list with a
  non-empty history looks like a failed fetch, not a delisting). Only the
  `coffee` and `single-origin` category archives are scraped.

## Sources

- https://atriumcoffeeroasters.com/
- https://atriumcoffeeroasters.com/product-category/single-origin/