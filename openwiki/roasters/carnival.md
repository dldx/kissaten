---
type: "Reference"
title: "Carnival Coffee Roasters — Roaster Profile"
description: "London-based speciality roaster (Shopify) known for distinctive fruit-forward filter, espresso and decaf coffees — including a Female Produced Coffee collection, tasting packs and coffee bundles."
---

# Carnival Coffee Roasters — Roaster Profile

## Overview

Carnival Coffee Roasters is a London-based speciality coffee roaster on a
Shopify storefront at carnivalcoffee.co.uk, known for distinctive,
fruit-forward filter, espresso and decaf coffees (e.g. Black Condor Colombia,
Efraín Gómez, Papayo, Pina Colada). The catalogue includes a "Female Produced
Coffee" collection, tasting packs and coffee bundles, and the beans are sold
in 230g bags (with 500g/1kg variants on some coffees). Local push-bike
delivery keeps it grounded in South East London.

## Address

- London, England — United Kingdom (no physical address published; the store
  mentions "South East London" push-bike delivery in its product pages).

## Philosophy & Quirks

- Curated filter (lighter roast, higher acidity) and espresso (classic,
  chocolate-and-nut, milk-friendly) ranges plus a dedicated decaf line.
- "Carnival Curiosities" limited runs of experimental coffees (e.g. Magnum
  Sidra, Efraín Gómez, Jennifer Delgado Sánchez) with vivid fruit-and-sweet
  tasting-note profiles.
- Female-produced coffee collection celebrating women producers (e.g. Maria
  Omaira, Jennifer Delgado Sánchez).
- An anniversary release — "Pina Colada – Colombia – 7th Birthday Coffee".

## Scraping Quirks

- NO master `/collections/coffee` (404) — the whole-bean catalogue is split
  across three `filter-coffee` + `espresso-coffee` + `delightful-decaf`
  products.json endpoints (28 raw products, 24 unique after dedup; the espresso
  decaf `espresso-decaf-black-condor` appears in two of the collections).
- Canonical product URLs are `/products/<handle>` (the collection segment is
  stripped; verified via `rel=canonical`).
- Tasting packs (`Tasting pack 4 x 100g`) are flagged `is_tasting_kit` /
  `requires_review`, not excluded; the espresso tasting pack does not resolve a
  single origin in its JSON and is currently dropped by the AI extraction.
- Brewing equipment (typed "Coffee brewing equipment") and workshop classes are
  excluded; named coffee bundles are retained as coffee products.

## Sources

- https://carnivalcoffee.co.uk
- https://carnivalcoffee.co.uk/collections/filter-coffee
- https://carnivalcoffee.co.uk/collections/espresso-coffee