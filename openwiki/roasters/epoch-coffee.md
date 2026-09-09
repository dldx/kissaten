---
type: "Reference"
title: "Epoch Chemistry — Roaster Profile"
description: "Moncton, New Brunswick roaster and coffee house built around a slow-coffee philosophy, best known for its numbered experimental series (Epoch 3, 6, 9, 12 and the rare Epoch X releases)"
---

# Epoch Chemistry

## Overview

Epoch Chemistry Coffee House is a specialty coffee roaster and café in Moncton,
New Brunswick, Canada ("proudly Canadian" per their site). Their storefront is a
Shopify shop selling beans organised into numbered series — Epoch 6 (decadent &
chocolatey), Epoch 9 (clean & bright), Epoch 3 (funky & wild), Epoch 12 (decaf
done right) and Epoch X (rare & remarkable) — plus instant coffee, brew gear,
merch and in-café coffee tasting experiences. The roastery/retail location is
their coffee house on St. George Street in downtown Moncton.

## Address

- 400 Saint George Street, Moncton, NB E1C 1X4, Canada (per their site's store-pickup data)

## Schedules & Shipping

- Online store orders ship on Tuesdays and Fridays weekly (per their site banner).
- Free Maritime (Atlantic Canada) shipping on Epoch beans over CAD $50; free
  shipping for the rest of Canada over CAD $75 (per their site banner).
- US shipping was temporarily on hold at the time of writing (per their site banner).

## Philosophy & Quirks

- They describe their ethos as "In Praise of Slow": coffee as a deliberate
  pause rather than a convenience product, inspired by the European coffee
  houses of the 17th and 18th centuries as "social equalizers" (per their site).
- Product naming is numeric rather than origin-first: the series number signals
  flavour direction (6 chocolatey, 9 clean/bright, 3 funky, 12 decaf), with
  individual beans carrying producer names (e.g. Epoch 3 - El Indio, Epoch 9 -
  Aponte Village Honey). Individual product pages do list producer, region,
  varietal and process details.

## Scraping Quirks

- The store is a Shopify Markets multi-currency shop (a country/region selector
  offers many currencies), so the scraper pins `store_currency = "CAD"` to avoid
  geo-converted prices.
- The site's curated "All Coffee" collection (`for-website-all-coffee`) does not
  list every published coffee — e.g. Epoch 12 - Decaf EA Palmera only appears in
  the "Nick's Picks" collection — so the scraper pulls both collections and
  dedupes on canonical `/products/<handle>` URLs.
- Coffee, instant coffee and coffee bundles in the curated collections flow
  through without slug exclusions; any kit-style bundle is expected to go through
  the tasting-kit review queue (`is_tasting_kit` / `requires_review`), never to
  be silently dropped.

## Sources

- https://epoch.coffee/
- https://epoch.coffee/pages/about-us
- https://epoch.coffee/products/epoch-3-pink-ranger-1
- https://epoch.coffee/collections/for-website-all-coffee/products.json
