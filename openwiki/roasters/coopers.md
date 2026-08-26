---
type: "Reference"
title: "Coopers Coffee — Roaster Profile"
description: "Specialty coffee roaster (Squarespace) roasted in Marlow, Buckinghamshire at Meter House, Fieldhouse Lane, selling single-origin and blended whole-bean coffees from a micro roastery."
---

# Coopers Coffee — Roaster Profile

## Overview

Coopers Coffee (cooperstradingcompany.com, Coopers Trading Company) is a
specialty coffee roaster based in Marlow, Buckinghamshire, selling single-
origin and blended whole-bean coffees roasted fresh from a micro roastery
("delicious sustainable coffee, roasted in Marlow"). It hosts a coffee bar in
addition to the shop and runs on a Squarespace Commerce storefront in GBP
(recovered from the dead cooperscoffee.co.uk domain).

## Address

- Coopers Trading Company, Meter House, Fieldhouse Lane, Marlow,
  Buckinghamshire, SL7 1LW — United Kingdom.

## Sourcing & Transparency

- Sustainably and ethically sourced: green coffee suppliers visit the farms
  and work closely with farmers and the local community (per their About
  page).

## Scraping Quirks

- Squarespace storefront; products live at `/shop/p/...` and are discovered
  from the `/shop` listing, skipping sold-out cards.
- `The Big 3!` curated sampler (multi-origin tasting box) is flagged
  `is_tasting_kit` in post-processing so it lands in the admin review queue
  rather than public search.
- Equipment (Hario cold-brew, Fellow Atmos, Keep Cups), classes, merch and
  green (unroasted) coffee are excluded; the "Jabbajaws" variant has an
  unpublished `price=None` on one size (known oddity).

## Sources

- https://cooperstradingcompany.com
- https://cooperstradingcompany.com/shop
- https://cooperstradingcompany.com/contact