---
type: "Reference"
title: "Leicester Coffee House — Roaster Profile"
description: "Independent Leicester city-centre coffee shop and roastery (Shopify) roasting six single origins weekly on 'Rocco' a Probatino roaster, with traceable sourcing, a circular-waste sustainability programme and free UK delivery over £22.50."
---

# Leicester Coffee House — Roaster Profile

## Overview

Leicester Coffee House Company (www.leicestercoffeehouse.co.uk) is a small
independent coffee shop and roastery in Leicester city centre (per their site),
on Shopify in GBP. The scraped catalogue is six whole-bean single origins plus
a 4 × 250g "Single Origin Coffee Selection" sampler; the shop also sells
keepcups, gift cards and gift wraps from a separate gifts collection. Beans are
roasted fresh each week in-house.

## Address

- 110 Granby Street, Leicester, LE1 1DL — United Kingdom (coffee shop).

## Sustainability

- Refillable-cup and container policy, part of the Leicester Refill water
  scheme, cycle delivery service for beans, and a circular-waste philosophy —
  coffee grits to community gardens, only compostable disposables, milk
  delivered in refillable glass bottles from a local dairy (per their
  sustainability page).

## Roasting & Equipment

- Roasted on "Rocco", a Probatino (Probat) drum roaster, in small batches
  throughout the week.

## Schedules & Shipping

- Orders are sent the next working weekday (Friday orders posted Monday,
  weekend orders Tuesday) via Royal Mail Tracked 48, arriving in 2–3 business
  days.
- Standard delivery £3.29; free UK delivery on orders over £22.50.

## Scraping Quirks

- Shopify; the curated `coffee-beans-freshly-roasted-coffee` collection is the
  whole-bean catalogue — 10 live products vs 17 claimed by the stale
  `collections.json` count (6 coffees + 1 sampler + 3 subscriptions).
- The Single Origin Coffee Selection sampler is kept and kit-flagged
  (`is_tasting_kit` / `requires_review`); the three subscriptions are excluded.
- `-copy` handles with mismatched titles (e.g. handle
  `mexico-cafe-el-zapoteco-anabel-chavez-copy` is titled "Indonesia - Ijen
  Highlands").
- Canonical www host and `/products/<handle>` URLs; currency pinned to GBP.

## Sources

- https://www.leicestercoffeehouse.co.uk
- https://www.leicestercoffeehouse.co.uk/collections/coffee-beans-freshly-roasted-coffee
- https://www.leicestercoffeehouse.co.uk/policies/shipping-policy
