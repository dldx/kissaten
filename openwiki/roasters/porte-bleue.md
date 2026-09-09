---
type: "Reference"
title: "Portebleue — Roaster Profile"
description: "Small-batch Montréal roaster roasting every bag to order on a P3000 hot-air roaster, with a lineup of wild-fermentation Colombian and Ethiopian single origins"
---

# Portebleue — Roaster Profile

## Overview

Portebleue is a small-batch specialty coffee roaster based in Montréal, Québec
(per their site). The storefront is Shopify. It is owned and run by Tanner
Gooding — Winnipeg-born, head roaster since moving to Montréal in 2015 — whose
current lineup is dominated by wild-fermentation Colombian lots (Wilder Lazo
Sidra, Ortega family Pink Bourbons) alongside Ethiopian and decaf offerings.
Local pickup is offered at "Portebleue HQ", and the shop also sells brewing
equipment, merch, and a "Portals" subscription.

## Address

- Montréal, Québec, Canada — full street address for the roastery is not
  published as a contact on site; the "Portebleue HQ" pickup location is
  referenced on product pages, and their Aeropress competition ticket page
  lists an event location at 465 rue de Port Royal O, Bureau 213, H3L 2C2,
  Montréal, QC, Canada (per their site).

## Roasting & Equipment

- Every bag is roasted to order on a P3000 hot-air roaster, with each roast
  followed closely for consistency (per their site).
- Green selection: importers short-list high-quality, sustainably farmed
  coffee; Portebleue sample-roasts short-listed lots before Tanner picks the
  most interesting coffees to feature (per their site).

## Schedules & Shipping

- Roasting cadence: roasted to order (per their site).
- Free shipping within Canada on B2C orders over $100 CAD (site-wide checkout
  banner). No per-region shipping rates are published beyond this.

## Philosophy & Quirks

- Roasts to order rather than holding stock — the site states "All coffee at
  Portebleue is meticulously curated and roasted to order" (per their site).
- Bean names are eclectic rather than descriptive of origin: "Wild Side",
  "Golden Hour", "Grape Gatsby", "Pretty in Pink", "Summer Cider" — with the
  producer, variety, process and a numeric roast level (e.g. "107.9", likely
  an Agtron-style score per their product pages) listed on each product page.
- Products carry b2b/b2c, coffee, Espresso and Filter tags; a wholesale store
  (with access request) sits behind the same Shopify shop.

## Scraping Quirks

- The curated `/collections/coffee` collection holds only beans, but the
  wider `/collections/all` catalog mixes in equipment (grinders, drippers,
  scales, filters), merch (hats, toques, totes), a subscription, and event
  tickets — the scraper must use the coffee collection, not `collections/all`.
- Each product page hides Variety / Process / Producer / Country / Tasting
  Notes / Roast Level inside a collapsed "Coffee Details" accordion that the
  products.json payload lacks, so page scraping is required (the accordion
  content is in the static HTML, so a soup prune suffices — no JS needed).
- Canonical product URLs have no collection segment
  (`/products/<handle>`), so `preprocess_product_url` strips the collection
  prefix.
- The store is CAD-only (single Canadian market; prices do not convert under
  `?country=` overrides), but the currency is pinned to CAD as a safeguard
  against Shopify Markets geo-localization.
- No tasting-kit/sampler products were in the coffee collection at the time
  of writing; any future kits must flow through with `is_tasting_kit` /
  `requires_review` flags rather than being excluded.

## Sources

- https://portebleue.ca/
- https://portebleue.ca/pages/about
- https://portebleue.ca/collections/coffee/products.json
- https://portebleue.ca/products/gloria-ortega
- https://portebleue.ca/policies/shipping-policy
