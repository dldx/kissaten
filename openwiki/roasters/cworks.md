---
type: "Reference"
title: "Cworks (The Coffeeworks) — Roaster Profile"
description: "UK roaster on a Shopify storefront known for dessert-inspired blends, half-caffeine roasts and single origins, with five curated sampler kits flowing through the review queue."
---

# Cworks (The Coffeeworks) — Roaster Profile

## Overview

Cworks, trading as The Coffeeworks (www.cworks.co.uk), is a UK roaster running
a Shopify storefront, known for dessert-inspired blends, a half-caffeine line
and single-origin coffees sold whole-bean or pre-ground. The curated whole-bean
catalogue lives in the `coffeebeans` collection.

## Address

- No roastery street address or town is published on the storefront. The site's
  schema.org Organization markup lists a registered office at 3rd Floor, Old
  Stock Exchange, St Nicholas Street, Bristol BS1 1TG, United Kingdom.

## Scraping Quirks

- Shopify products.json from the curated `coffeebeans` collection; the whole-bean
  set is that collection minus the gift card and `bundle-deal` combo packs.
- 5 curated multi-bean sampler sets (Best Sellers, Big & Bold, Home Barista,
  The Milkies, The Low Caffeine) are retained and flagged `is_tasting_kit` /
  `requires_review` into the admin review queue, never excluded.
- 3 blends persistently fail AI extraction (milk-chocolate-blend,
  marzipan-truffle-blend, fruit-nut-blend-new-1); out-of-stock updates are
  guarded so they are not misreported.
- e2e: 27 saved + 5 kit flags.

## Sources

- https://www.cworks.co.uk
- https://www.cworks.co.uk/collections/coffeebeans
- https://www.cworks.co.uk/pages/contact-us