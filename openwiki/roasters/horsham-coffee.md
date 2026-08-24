---
type: "Reference"
title: "Horsham Coffee Roaster — Roaster Profile"
description: "West Sussex specialty roaster on Shopify at horshamcoffeeroaster.co.uk roasting on a Loring S35 eco-roaster with direct sourcing from Costa Rica, Rwanda, Kenya and Brazil, the Bwishaza Goat Project and a 4300+ review storefront weighted towards brewing equipment."
---

# Horsham Coffee Roaster — Roaster Profile

## Overview

Horsham Coffee Roaster is an independent West Sussex specialty roaster (named
for the market town) on a Shopify storefront at horshamcoffeeroaster.co.uk,
roasting on a Loring S35 eco-roaster with direct sourcing from Costa Rica,
Rwanda, Kenya and Brazil and 4,300+ reviews. The store is heavily weighted
towards brewing equipment around a curated whole-bean coffee range.

## Address

- Unit 5, 1a William Way, Burgess Hill RH15 9AG — United Kingdom (per the
  site's contact-information page).

## Sourcing & Transparency

- Direct-trade model with long-term producer relationships; "Relationship
  Coffee" label introduced 2017; single origins targeted at 84+ on SCA/CQI.
- Rwanda: sourcing since 2015 with the Gishyita cooperative (donated $1,000
  in 2016, Shye school repair 2017); Costa Rica via Selva Coffee since 2020.
- Bwishaza Goat Project: £1 per bag of selected Bwishaza coffees plus matched
  donations — £3,000 funded 77 goats in April 2026, ten years with the co-op.

## Roasting & Equipment

- Loring S35 eco-roaster (per the homepage).

## Schedules & Shipping

- Free UK delivery over £25 (£2.25 under £25; mainland over £20 free tracked);
  next-working-day dispatch before midnight; coffee sent within 7 days of roast.

## Scraping Quirks

- Shopify; the single curated `coffee-beans` collection is the superset of
  blends / single-origin / filter / espresso / decaf (verified union — no
  merge needed).
- `workhorse-blend-coffee-pods` (Nespresso capsules) and
  `coffee-of-the-month-subscription` excluded by slug — the base class does
  NOT exclude pods.
- `single-origin-coffee-selection` and `coffee-blend-selection` 4-bag samplers
  kept and flagged `is_tasting_kit` / `requires_review` for the admin queue.
- Canonical product URLs are `www.horshamcoffeeroaster.co.uk/products/<handle>`
  (the bare host 302s to www).

## Sources

- https://www.horshamcoffeeroaster.co.uk
- https://www.horshamcoffeeroaster.co.uk/pages/source-coffee
- https://www.horshamcoffeeroaster.co.uk/pages/the-bwishaza-goat-project
- https://www.horshamcoffeeroaster.co.uk/policies/shipping-policy
- https://www.horshamcoffeeroaster.co.uk/policies/contact-information
