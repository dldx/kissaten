---
type: "Reference"
title: "Conscious Coffee — Roaster Profile"
description: "Conscious Coffees (consciouscoffees.com) is an organic fair-trade coffee company based in Boulder, Colorado, USA on a Shopify storefront, selling a curated coffee collection roasted to order."
---

# Conscious Coffee — Roaster Profile

## Overview

Conscious Coffee (consciouscoffees.com, trading as Conscious Coffees) is a
Boulder, Colorado, USA coffee company on a Shopify storefront, claiming to
have "been setting industry standards for 30 years" and brand-positioned as
"Colorado's finest organic, fair trade coffee". The catalogue is a curated
`coffees` collection of single origins, blends and decaf plus an 8oz sampler,
priced in USD. Note: despite appearing in Kissaten's UK tracking batch, the
live site is a US company — the scraper registry is correctly
`country="United States"` / `currency="USD"`.

## Address

- Mailing address published on the contact page: 5403 Western Ave, Suite B,
  Boulder, CO 80301 — United States. (Full roastery address not further
  specified on site.)

## Sourcing & Transparency

- 100% organic and fair-trade positioning throughout (per site nav and
  homepage copy); "the world needs more happy people" tagline on the contact
  page.

## Scraping Quirks

- Shopify using the curated `coffees` collection rather than
  `collections/all`, which mixes in merch, T-shirts, KeepCups, subscriptions
  and gift cards.
- Green (unroasted) coffee is excluded; the `conscious-coffees-8oz-sampler-4-pack`
  handle carries `sampler`, so it is flagged `is_tasting_kit` /
  `requires_review` and flows through the admin review queue.
- Homepage widget prices display in USD; the scraper pins `store_currency`
  defensively so geo-detection cannot overwrite it.
- Registry metadata is `country="United States"` / `currency="USD"`. This
  profile exists as a US "guest" roaster, kept as its own scraper distinct
  from the UK Conscious entity at consciousspeciality.com (tracked under a
  different registry slug).

## Sources

- https://consciouscoffees.com
- https://consciouscoffees.com/pages/contact
- https://consciouscoffees.com/collections/coffees/products.json