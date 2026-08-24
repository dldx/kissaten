---
type: "Reference"
title: "Campbell & Syme — Roaster Profile"
description: "London coffee roaster and café founded in 2012 (East Finchley café at 9 Fortis Green; roastery in Kings Langley) selling curated 250g/1kg single origins and blends from a Shopify storefront."
---

# Campbell & Syme — Roaster Profile

## Overview

Campbell & Syme is a London coffee roaster with a Shopify storefront at
campbellandsyme.co.uk. Founded in 2012 by Joe Syme after falling for the
specialty coffee scene in Portland, Oregon, it runs its flagship café at 9
Fortis Green in East Finchley and roasts in Kings Langley. The curated "250G &
1KG" shop collection carries 13 single-origin/blend coffees priced in GBP
(FORTIS GREEN £11.50, HAMBELLA £14.75, LALESA £17.00, a BALACOBACO Daterra
"Masterpiece" pre-release at £27.50). The business also runs classes and
events and sells brewing equipment plus gift subscriptions.

## Address

- Café: 9 Fortis Green, East Finchley, London N2 9JR — United Kingdom
- Roastery: Unit 3, Monaco Works, Station Rd, Kings Langley WD4 8LQ — United
  Kingdom (visits by appointment)

## Philosophy & Quirks

- Pre-release and limited lots, e.g. the BALACOBACO (Daterra "Masterpiece")
  Brazil offering is published with a `pre-release` handle while still in
  limited release.
- Origin-focused single bags at 250g and 1kg, with a twice-weekly shipping
  schedule (orders after 10am Tuesday ship Thursday, and vice versa).
- "Collective effort" ethos — roasting is shared with wholesale companions,
  café customers and the online community.

## Scraping Quirks

- No master `/collections/coffee` (it 404s) — the curated coffee collection is
  `/collections/shop-page` ("250G & 1KG"), which carries only coffee beans.
- A `sample-box` tasting-kit collection exists but is **not** scraped; even so,
  sampler/taster handles are never excluded (flag-don't-exclude across kits) —
  the base class flags them for review instead.
- `product_type` is empty on 3 of the 13 products (the rest are typed "Coffee
  beans"), so those products rely on title-based heuristics.
- Storefront can geo-locate the datacenter IP to a non-GBP market, so the
  scraper pins the home GBP currency.

## Sources

- https://campbellandsyme.co.uk
- https://campbellandsyme.co.uk/pages/location
- https://campbellandsyme.co.uk/collections/shop-page