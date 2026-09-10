---
type: "Reference"
title: "Glass Coffee — Roaster Profile"
description: "Camden BoxPark roaster built on radical transparency — Transparent Pricing with green-bean and transport costs on every product page, Roast Cards publishing the actual roast curve, and every ingredient from a single named farm."
---

# Glass Coffee — Roaster Profile

## Overview

Glass Coffee is a transparency-obsessed specialty roaster and coffee shop at
**BoxPark Camden Town, London**, founded by Carlo, who was born and raised in
Brazil and started the company after graduating from the University of Warwick,
with co-founders Lampros Sekliziotis and Konstantinos Dalkafoukis. Every
ingredient in the shop — coffee and otherwise — is sourced from **individual
farms** and presented with full traceability: "We share the farm, the people,
and the route it took to reach you." The catalogue leans into experimental
fermentation and rare lots: Wilder Lazo's Bella Alejandría Gesha (300 hours of
cherry fermentation), the Hachi Project Panama Gesha, Sebastián Ramirez's Finca
El Placer (the first farmer they bought green coffee from directly), and
Hacienda Esmeralda.

## Address

- London, United Kingdom — a separate roastery address is not published on the
  site; their store is at First Floor, Unit 49, BoxPark, 192–198 Camden High
  Street, London NW1 8QP

## Sourcing & Transparency

- **Transparent Pricing on every product page** (launched 2025): green-bean
  cost per kg, per-kilogram transport cost, and lot size, in GBP — e.g.
  green bean £62.00 + transport £3.00, lot size 30 kg, material cost £65.00,
  total £1,950.00. They deliberately show only material costs, excluding
  roasting, rent, taxes, and labour.
- A **Transparent Pricing 2.0** roadmap plans blockchain-verified cost data,
  piloted with one of their farmers (per their site).
- All coffees and other ingredients are "exclusively obtained from individual
  farms" to guarantee traceability, which they argue against blending as a
  cost-stabiliser.
- Producer pages profile the people behind the lots (Sebastián Ramirez, José
  Jijón, Wilder Heiner and Segundo Lasso, Hacienda Esmeralda, Finca Nogales,
  Hacienda Copey, Bette Buna, and more).

## Roasting & Equipment

- **Roast Cards**: each product page carries a reference roast card plotting
  four temperatures (hot air, drum surface, bean surface, internal bean) across
  drying, yellowing, and development phases, with turning point, first crack,
  target end temperature, phase durations/percentages, and ground-bean and
  whole-bean roast colour readings on a medium-to-ultra-light scale.
- The order-confirmation email carries a **batch card** with the actual roast —
  batch ID, batch size, roast date/time, and the name of the operator who
  pulled the batch.
- They roast to tight tolerances — "typically within a degree of release
  temperature" — observing that small windows (sometimes ~15 seconds at the end
  of a roast) decide where the cup lands.

## Philosophy & Quirks

- Ethos: "**Transparency as Trust**" and "Don't trust, verify" — transparency
  treated as "our currency for trust" rather than marketing.
- The name Glass reflects the mission of making an opaque industry see-through;
  the company started as a "Minimum Valuable Product" built by a team met at
  Warwick University and the Geovation Hub.
- Beyond coffee they trace non-coffee ingredients too — matcha from Obubu,
  oolong from Marulin, chamomile from Tregothnan, Isle of Skye sea salt,
  Summerdown peppermint and lavender, Santana panela — each with its own
  producer page.

## Scraping Quirks

- **Pagination is hardcoded**: the scraper fetches two fixed collection URLs
  (`/collections/coffee?page=2`, both with `filter.v.availability=1`), so page
  counts beyond two would be missed if the catalogue grows.
- **Sold-out products are filtered out at URL-extraction time** — product tiles
  containing a "Sold out" label are skipped, so sold-out coffees drop out of
  the catalogue until back in stock.
- Only the **first `.product-grid`** element on the collection page is read for
  product links.

## Sources

- https://glasscoffee.co.uk
- https://glasscoffee.co.uk/pages/about-glass-coffee
- https://glasscoffee.co.uk/pages/introducing-transparent-pricing-at-glass-coffee-a-new-era-of-clarity-for-every-cup
- https://glasscoffee.co.uk/pages/roast-curve
- https://glasscoffee.co.uk/pages/cost-of-sustainability-traceability
- https://glasscoffee.co.uk/pages/camden-store
