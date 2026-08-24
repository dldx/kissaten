---
type: "Reference"
title: "Clifton Coffee Roasters — Roaster Profile"
description: "Bristol-based coffee roaster (Shopify) with house espresso works, a rotating single-origin filter range, organic options, Sugarcane decaf, plus tea, matcha & chai, capsules and merch."
---

# Clifton Coffee Roasters — Roaster Profile

## Overview

Clifton Coffee Roasters is a Bristol-based coffee roaster on a Shopify
storefront at cliftoncoffee.co.uk. The curated "All Coffee" collection carries
20 products — anchors of the range are Suspension Espresso, Village Organic,
E1 Project Espresso, Cadence Espresso, House Filter and Sugarcane Decaf, plus a
rotating set of single origins, with "Freshly Roasted in Bristol" same-day
dispatch. The store also sells tea, matcha & chai, Nespresso-style capsules and
brewing merchandise.

## Address

- Island Trade Park, Bristow Broadway, Bristol BS11 9FB — United Kingdom

## Philosophy & Quirks

- House espresso works plus a rotating single-origin filter schedule; an
  "Unparalleled Series" of experimental coffees (e.g. Ombligon – Finca El
  Diviso).
- Organic options (Village Organic Espresso from Honduras' Comucap
  Cooperative).
- Sugarcane Decaf — coffee decaffeinated via the sugar-cane ethyl-acetate
  process.

## Scraping Quirks

- Canonical product URLs are `/products/<handle>` (no collection segment) and
  some handles carry a `-1` suffix (e.g. `colombia-finca-las-flores-1`).
- The `coffee` collection also contains non-bean items (Nespresso capsules,
  branded storage tins), which are excluded via `capsules` / `coffee-tin`
  slugs (~16 beans of 20).
- A `testroast` test product is excluded from scraper results.

## Sources

- https://cliftoncoffee.co.uk
- https://cliftoncoffee.co.uk/pages/contact
- https://cliftoncoffee.co.uk/collections/coffee