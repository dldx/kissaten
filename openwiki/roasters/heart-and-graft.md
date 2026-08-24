---
type: "Reference"
title: "Heart & Graft — Roaster Profile"
description: "Manchester specialty roaster ('Speciality Coffee Roasted in Manchester') on WooCommerce/Shopkeeper — house blends/singles and single origins, plus Discovery Box and Archetype Collection samplers that flow through the review queue."
---

# Heart & Graft — Roaster Profile

## Overview

Heart & Graft is a Manchester specialty roaster ("Speciality Coffee Roasted
in Manchester" per the site title) on a WordPress WooCommerce + Shopkeeper
storefront at heartandgraft.co.uk. Its `/shop/coffee/` listing carries ~10
coffee products priced in GBP — the 60/40 blend, Barnraiser, Highroad, Brazil
Santa Rosa, Colombia El Buho Sugarcane Decaf, Ethiopia Rumudamo, Guatemala
Paya', the Archetype Collection sampler and the Discovery Box sampler — plus
recurring coffee subscriptions.

## Address

- 21 North Street, Manchester — United Kingdom.

## Schedules & Shipping

- Free tracked shipping on orders over £20.

## Philosophy & Quirks

- Manchester-based roasting with house blends, house singles and single
  origins.
- A 60/40 blend and a sugarcane-processed decaf (Colombia El Buho).
- Discovery Box and Archetype Collection samplers, both flagged as tasting
  kits into the admin review queue.

## Scraping Quirks

- WooCommerce (no products.json) — coffee lives under `/shop/coffee/` plus the
  house-blends / house-singles / single-origin subcategories, which are
  crawled and deduplicated so a promoted product is not lost.
- The `discovery-box` coffee sampler would be wrongly dropped by the base
  `"discovery"` exclusion pattern — the scraper uses explicit slug matching
  instead so it flows through and is flagged `is_tasting_kit` (verified e2e:
  Discovery Box kit=True, price=None — admin fills price on review).
- Recurring `*-subscription` coffee plans are excluded; brewing equipment and
  merch-and-curios live on separate category paths that are never crawled.
- Currency is pinned to GBP.

## Sources

- https://heartandgraft.co.uk
- https://heartandgraft.co.uk/shop/coffee/