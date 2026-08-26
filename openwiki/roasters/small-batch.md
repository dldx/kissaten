---
type: "Reference"
title: "Small Batch Coffee Roasters — Roaster Profile"
description: "Brighton & Hove specialty roaster (est. 2006) and one of the UK's specialty-coffee pioneers, roasting fresh to order from Wellington House, Portslade on Shopify with free delivery over £25."
---

# Small Batch Coffee Roasters — Roaster Profile

## Overview

Small Batch Coffee Roasters (smallbatchcoffeeroasters.co.uk) is a specialty
coffee roaster based in Brighton & Hove since 2006 and, per their site, one of
the pioneers of specialty coffee in the UK. It roasts from its award-winning
Brighton Roastery at Wellington House, Portslade, for two cafés, a coffee cart
and wholesale. The Shopify storefront (GBP) carries a curated range of
espresso/blend and single-origin beans plus tasting sets.

## Address

- Brighton Roastery, Wellington House, Portslade, Brighton & Hove BN41 1DU,
  United Kingdom (published on the site; cafés in Hove are separate outlets).

## Schedules & Shipping

- All orders are roasted fresh to order within 2 working days of receipt, then
  allow 3–5 days for delivery (per their site).
- Free delivery on all orders over £25.

## Scraping Quirks

- Domain correction: the legacy `smallbatchcoffee.co.uk` host redirects to the
  `www.smallbatchcoffeeroasters.co.uk` Shopify storefront.
- Shopify; the curated `all-coffee` collection mixes non-coffee items (pods,
  bundles, subscriptions, chocolate) that are filtered out — `product_type` is
  empty across the feed, so filtering is by slug.
- Global Discovery Kit and Global Connoisseur Set are tasting kits, extracted
  and flagged `is_tasting_kit` / `requires_review` into the admin review
  queue (never excluded).
- 12 of 17 products saved; 5 catalogue entries recur as persistent
  AI-extraction failures (guarded out-of-stock updates).

## Sources

- https://www.smallbatchcoffeeroasters.co.uk
- https://www.smallbatchcoffeeroasters.co.uk/pages/about-small-batch-coffee-roasters
- https://www.smallbatchcoffeeroasters.co.uk/pages/shipping-and-delivery