---
type: "Reference"
title: "Got Coffee Co. — Roaster Profile"
description: "Tiny Shopify-based roaster in Horseshoe Valley, Ontario, selling a rotating trio of single origins alongside a coffee subscription and pop-up cafe events."
---

# Got Coffee Co. — Roaster Profile

## Overview

Got Coffee Co. is a small Canadian roaster based in Horseshoe Valley, Ontario,
Canada, that roasts "thoughtfully sourced beans" and sells them through a
Shopify storefront (per their site). The catalogue is tiny — three single-origin
bags at a time (a Brazil, a Colombia and a Colombian sugarcane-EA decaf) —
plus a "Classic Subscription" and merch. The brand is closely tied to pop-up
cafe events; their newsletter sign-up is framed around "new coffee drops and
future pop-up cafe dates".

## Address

- Horseshoe Valley, Ontario, Canada — full roastery street address not published on site.

## Sourcing & Transparency

Product descriptions name producers, farms and importers per lot (per their
site): Brazil - Fazenda Esperança (Deyvid Leandro, Cerrado Mineiro, imported
by Orange Brown Coffee), Nariño Reserve - Colombia (various smallholders,
sourced by Andres Martinez) and El Placer - Traditional Decaf (Sebastian
Ramirez, Quindío, imported by Macarena Coffee Importers). No FOB or
farm-gate price figures are published.

## Schedules & Shipping

- Free shipping within Canada with 3+ bags (site banner). No minimum order
  value is published — the threshold is a bag count, not an amount.
- No roast/dispatch schedule is published on the site.

## Philosophy & Quirks

- Operates as a pop-up roaster: the online shop carries a deliberately small,
  rotating set of coffees while in-person presence happens at pop-up cafe
  dates (per their site).
- Sells a "Coffee Dad" t-shirt alongside the beans — the merch/subscription
  share of the catalogue is large relative to the coffee itself.

## Scraping Quirks

- There is no curated coffee collection; the scraper must use
  `/collections/all/products.json` and exclude the subscription, gift card
  and apparel handles by slug.
- The site's canonical product URLs have no collection segment
  (`/products/<handle>`), so the scraper strips `/collections/all/` from
  product URLs built from the products.json base.
- The store serves CAD natively, but the currency is pinned in the scraper to
  guard against Shopify Markets geo-conversion.

## Sources

- https://gotcoffee.co
- https://gotcoffee.co/collections/all/products.json
- https://gotcoffee.co/pages/contact
