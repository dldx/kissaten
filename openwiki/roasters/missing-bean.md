---
type: "Reference"
title: "Missing Bean — Roaster Profile"
description: "Oxford specialty coffee roaster (Shopify) roasting direct-trade single origins at its East Oxford roastery since 2014, with free UK delivery over £33 and a UK-wide café family."
---

# Missing Bean — Roaster Profile

## Overview

Missing Bean (www.themissingbean.co.uk) is an independent specialty coffee
company founded in Oxford in 2009 that established its own East Oxford
roastery in 2014 (per their site). It is on Shopify in GBP; the curated
`coffee` ("Coffee Beans") collection is the whole-bean catalogue — 15
single-origin/blend coffees plus a Multi-Coffee Sample Box sampler (16
products; the collection's 17 Coffee-type products include a subscription).
The company has grown from a single Turl Street café into a family of cafés
across Oxfordshire plus a bakery.

## Address

- Roastery Café — 1 Newtec Place, Magdalen Road, Oxford, OX4 1RE — United
  Kingdom.
- Original café — 14 Turl Street, Oxford — United Kingdom.
- Further cafés in Botley, Woodstock, Charlbury, Cowley, Abingdon and
  Maidenhead (per their site).

## Sourcing & Transparency

- Direct-trade sourcing: works directly with producers so farmers receive
  fair prices, with documented sourcing trips on their direct-trade blog.
- Direct-trade farm coffees named on product pages (e.g. Colombia El Calapo,
  Mexico Finca Hamburgo, Nicaragua El Jaguar, Kenya Gloria & Jane). No
  per-bag FOB/price-to-producer figures published (per their site).

## Schedules & Shipping

- Roasted every weekday at the East Oxford Roastery (five days a week).
- Order by 11am Mon–Fri for same-day dispatch from the Roastery.
- Free delivery on orders of £33+ or 1–2kg; standard UK £3.95 (Royal Mail 2nd
  Class, up to 4 working days); next-working-day £6.55 (Parcel Force);
  eco-friendly local (Oxford OX1–OX4) £2.40.

## Scraping Quirks

- Shopify; the curated `coffee` collection is the whole-bean catalogue — the
  `collections.json` count is stale/inflated and untrusted. Filtering on
  `product_type == "Coffee"` drops a lone Gift Voucher; the subscription is
  excluded by slug.
- The Multi-Coffee Sample Tasting Box flows through and is kit-flagged
  (`is_tasting_kit` / `requires_review`) for the admin review queue, never
  excluded.
- Canonical `/products/<slug>` URLs; the `/collections/coffee` segment is
  stripped. Currency pinned to GBP.

## Sources

- https://www.themissingbean.co.uk
- https://www.themissingbean.co.uk/pages/delivery-information
- https://www.themissingbean.co.uk/pages/east-oxford-roastery