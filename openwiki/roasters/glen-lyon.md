---
type: "Reference"
title: "Glen Lyon Coffee Roasters — Roaster Profile"
description: "Perthshire (Aberfeldy) coffee roaster on Shopify, organised by origin (Africa/Asia/Brazil/Colombia/Central America…) with 58 coffee products and curated sampler boxes that flow through the review queue."
---

# Glen Lyon Coffee Roasters — Roaster Profile

## Overview

Glen Lyon Coffee Roasters is a Scottish specialty coffee roaster based in
Perthshire, on a Shopify storefront at glenlyoncoffee.co.uk. Its curated
`coffee` collection carries 58 products priced in GBP, e.g. Red Stag Espresso
£12.50, True North Guatemala, West Coast Roast, Colombia Carolina Samboni
Pink Bourbon £14.75, Ethiopia Bette Buna £14.00, Peru Neyra Chininin Gesha and
organic-certified lots such as Peru Organic Salkantay. The catalogue is
organised by origin (Africa, Asia, Brazil, Burundi, Colombia, Central
America, Rwanda…).

## Address

- Aberfeldy Business Park, Aberfeldy, Perthshire — United Kingdom (per the
  site's schema.org address markup).

## Schedules & Shipping

- Free UK shipping on subscriptions and all orders over £25.

## Philosophy & Quirks

- Origin-organised catalogue (single origins grouped by country/region).
- Curated sampler boxes — Mocha Box, Low Caff Duo, quartet boxes and trio
  boxes — all flagged as tasting kits into the admin review queue.

## Scraping Quirks

- The curated `coffee` collection holds 59 raw products; the one recurring
  single-origin subscription is excluded, leaving 58 in the catalogue.
- Canonical product URLs are `/products/<handle>` on the `www` host (the
  collection segment is stripped and `www` is forced).
- Sampler boxes (trio/duo/quartet/mocha) are retained and flagged
  `is_tasting_kit` via an override of `_get_tasting_kit_url_patterns`, not
  dropped.
- Currency is pinned to GBP.

## Sources

- https://glenlyoncoffee.co.uk
- https://glenlyoncoffee.co.uk/collections/coffee