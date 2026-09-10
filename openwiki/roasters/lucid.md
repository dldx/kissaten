---
type: "Reference"
title: "Lucid Coffee Roasters — Roaster Profile"
description: "Belfast roastery founded in 2021 by Stephen Houston — per-coffee green price and importer listings (FOB where consented), rice-paper packaging, an annual transparency-report pledge and roast profiles shared with Agtron readings."
---

# Lucid Coffee Roasters — Roaster Profile

## Overview

Lucid Coffee Roasters was founded in Belfast in 2021 by Stephen Houston, "a
well known coffee professional" with a decade of roasting experience and a
shelf of competition titles (Irish Brewers Cup Champion 2017 & 2019, Irish
AeroPress Champion 2019, UK SCA Roasting Championships 2nd place 2023, Irish
Cup Tasters 3rd place 2026, past Chair of the Coffee Roasters Guild — per
their site). The name means "to be expressed clearly, easy to understand,
vivid", and the mission is to be "transparent at every step of the production
line". The Shopify storefront sells filter and espresso single origins in
250g/1kg, plus subscriptions.

## Address

- Unit 5, Kennedy Way, Belfast BT11 9AP — United Kingdom (published as "Visit
  us" on every page; Mon–Fri 9–5 roastery/visit address)

## Sustainability

- **Rice paper packaging** from renewable sources (Qintan tree bark and
  bamboo), with recyclable degassing valves and resealable zippers; all boxes
  and tape fully recyclable.
- Roastery fit-out from re-found and up-cycled materials — the cupping table
  and test-area cupboards come from an up-cycled kitchen, shelving is
  second-hand.
- Carbon offsetting via offset projects and carbon-neutral couriers; larger
  green purchases to reduce road/sea/air deliveries.
- Stated goals (not yet achieved, per their site): full carbon neutrality,
  1% for the Planet membership, a 100% electric delivery van, an afterburner
  on the roaster, and solar/renewable electricity.

## Sourcing & Transparency

- A dedicated **Transparency** page commits to: sharing the **FOB price over
  the farm-gate price** (where producers consent) *and* the price paid to the
  importer/exporter per kg, sharing **roast profiles and Agtron readings** for
  every coffee, not biasing toward 85+ coffees so producers of 80–86 lots keep
  a sustainable outlet, and producing a **transparency report every year**.
- In practice, coffee product pages carry a data block, e.g. Kenya
  Gichatha-ini AA lists producer, farm, **Importer: Cofinet**,
  **Price (green ex Shipping): £14.20/kg** and **Amount Bought: 60kg**.
- Staff are paid a real living wage, with profits reinvested into training,
  community projects and carbon neutrality (per their site).

## Roasting & Equipment

- Not named on the site. Founder credentials mention "over 25,000 production
  roasts via a number of roasting machines from 100g to 120kg" (per their
  site); no roaster brand/model is published.

## Schedules & Shipping

- Shipping policy: **UK by Royal Mail 24hr + 48hr, Republic of Ireland and
  Europe by DPD, worldwide by DHL**. No free-delivery minimum or per-region
  rates are published on the policy page.
- Roast/dispatch cadence is not published; opening hours are Mon–Fri 9–5
  (closed weekends).

## Philosophy & Quirks

- "Clearly expressed and easy to understand. This is how coffee should be,
  clear, expressive and accessible to everyone." — transparency as the whole
  brand.
- Sells **"Rested / Test Roasts"** bags — experimental or aged roasts sold as
  a budget line alongside the main range.
- Collaboration and sponsorship pages (Lucid Collaborations / Lucid
  Sponsorship) and limited merch runs like the "4th Birthday Tee" illustrated
  by Ferns & Pen.

## Scraping Quirks

- **URL canonicalisation dedup**: products appear under multiple collection
  URLs, so `preprocess_product_url` collapses every
  `/collections/<slug>/products/<handle>` onto the canonical
  `/products/<handle>` form to avoid duplicate listings.
- **Broad exclusion slugs must stay brand-specific**: bean handles use
  `-filter`/`-espresso` as roast-style suffixes (e.g. `kenya-gichatha-ini-aa-
  filter`), so generic slugs like `filter` or `grinder` would wrongly drop
  real beans — only distinctive slugs (`orea`, `sibarist`, `bwt`, `aiden`,
  `lucid-sporty-socks`, `t-shirt`, `collab-a3-print`, …) are safe to exclude.

## Sources

- https://www.lucidcoffeeroasters.com/
- https://www.lucidcoffeeroasters.com/pages/copy-of-about-us
- https://www.lucidcoffeeroasters.com/pages/transparency
- https://www.lucidcoffeeroasters.com/pages/environmental-impact
- https://www.lucidcoffeeroasters.com/policies/shipping-policy
- https://www.lucidcoffeeroasters.com/products/kenya-gichatha-ini-aa-filter
