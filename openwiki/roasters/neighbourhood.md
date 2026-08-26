---
type: "Reference"
title: "Neighbourhood Coffee — Roaster Profile"
description: "Liverpool specialty roaster ('Liverpool's smiliest specialty coffee roasters') on WooCommerce, selling whole-bean coffees, brewing gear and subscriptions from Unit 22, The Sandon Estate."
---

# Neighbourhood Coffee — Roaster Profile

## Overview

Neighbourhood Coffee (www.neighbourhoodcoffee.co.uk) is a Liverpool specialty
roaster — "Liverpool's smiliest specialty coffee roasters" — running a
WordPress + WooCommerce storefront. The whole-bean catalogue (blends and
single-origin coffees grouped by growing region) sits alongside a large coffee
equipment range, gifting and subscriptions.

## Address

- Unit 22, The Sandon Estate, Sandon Way, Liverpool L5 9YN, United Kingdom.

## Scraping Quirks

- WooCommerce Store API (unauthenticated `/wp-json/wc/store/v1/products`) is
  used for discovery; the large equipment catalogue, gifts and coffee
  subscriptions are dropped, keeping only whole-bean coffee categories.
- The `fab-pour-collection` sampler is retained and flagged
  `is_tasting_kit` / `requires_review` into the admin review queue.
- e2e: 17 saved + 1 kit flag.

## Sources

- https://www.neighbourhoodcoffee.co.uk
- https://www.neighbourhoodcoffee.co.uk/liverpool/
- https://www.neighbourhoodcoffee.co.uk/contact-us/