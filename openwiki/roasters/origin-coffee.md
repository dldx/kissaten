---
type: "Reference"
title: "Origin Coffee Roasters — Roaster Profile"
description: "Porthleven, Cornwall roastery founded 2004 — B Corp certified (score 95.6), a new coffee released every week, FOB/cup-score transparency on every product page, and sail-shipped coffee."
---

# Origin Coffee Roasters — Roaster Profile

## Overview

Origin Coffee is one of Europe's leading speciality roasters, founded in 2004
by Tom Sobey and headquartered at The Roastery in Porthleven, Cornwall — one
of the longest-standing speciality roasters in the UK (per their site). The
company runs seven coffee shops (Porthleven, Bristol, Shoreditch, the British
Library and Southwark in London, and Edinburgh) and releases a new coffee
every week — "52 coffees released in a year". Shopify storefront at
[origincoffee.co.uk](https://www.origincoffee.co.uk).

## Address

- The Roastery, 1 Treysa Place, Porthleven, Cornwall TR13 9FJ — United
  Kingdom (roastery with sit-in coffee shop, QC and training rooms)

## Sustainability

- B Corp certified since 2020 with a verified score of 81.9; latest
  re-certification score **95.6** (reviewed every three years by B Lab).
- Net Zero commitment: measured a 2022 baseline carbon footprint and uses the
  Science Based Targets initiative (SBTi) tool for a pathway to Net Zero "well
  ahead of 2050" (per their site).
- Publishes annual sustainability reports and an environmental policy.
- Coffee-bag recycling scheme ("Recycle Rewards") and letterbox-friendly,
  size-constrained packaging for 1–2 × 250 g orders.

## Sourcing & Transparency

- Direct Trade with their own published definition: the price, contract and
  relationship roaster and producer directly agree — pricing set "always above
  Fairtrade and C market prices" (per their site).
- Product pages carry a transparency block with **cup score and FOB price**
  alongside provenance (producer, variety, elevation, process) — the scraper
  extracts exactly that accordion.
- "Shipped by Sail": a project trialling sail-powered coffee transport,
  billed as "setting a new standard for responsible sourcing" (per their
  journal).

## Roasting & Equipment

- Roasting is done at the Porthleven roastery; a team of roasters and Q
  Graders applies "meticulous sensory measures throughout every stage of
  roasting". No specific machine is named on the site.
- Roast profile is described as light: "Roasting lightly. Respecting the
  beans."

## Schedules & Shipping

- Roasted to order; order before 23:59 and coffee is roasted and despatched
  the next day (orders after 23:59 Thursday despatch Monday).
- Free Royal Mail Tracked 48 on UK orders over **£35**; under £35: Tracked 48
  £2.95 / Tracked 24 £3.95 (Tracked 24 is £1.95 over £35). Orders over 2 kg
  ship DPD next day free.
- International flat rates: Europe £12.95, North America £14.95, Rest of
  World £19.95 (no >1.75 kg outside the UK).
- Subscription orders always ship Royal Mail Tracked 48 free.

## Philosophy & Quirks

- Accolades per their site: UK Barista Championships winner 2016 & 2018, UK
  Cup Tasters winner 2020, World Coffee in Good Spirits winner 2018 & 2019.
- Runs an SCA-aligned education programme (SCA Barista/Brewing/Sensory
  courses, roasting workshops) from the roastery and a dedicated Cold Brew
  Brewery site.
- Signature range: Resolute (their flagship house espresso) alongside a
  rotating weekly single-origin release.

## Scraping Quirks

- Same coffee appears across several overlapping collections (`coffee`,
  `single-origin-coffee-beans`, `coffee-blends`, `espresso-coffee`,
  `filter-coffee`, `decaf-coffee-beans`); the scraper fetches them all and
  canonicalises every URL to `/products/<handle>` (and forces the `www` host)
  so duplicates collapse.
- AI extraction is deliberately limited to the product page's
  `ul.info__fields` accordion (Story / Provenance / Transparency with cup
  score + FOB price / Brewing recipe) to keep the prompt small.
- The base-class name filter drops titles containing "fellow" (equipment
  guard), but Origin appends competition copy like "Resolute + Fellow Series
  One Competition Entry" to coffee titles — the scraper strips the
  `+ Fellow Series X Competition Entry` tail before the filter so those
  coffees are not lost.
- `mug` is intentionally absent from the exclusion slugs: the bean
  `mugaga-kagumoini` contains it as a substring and would be wrongly dropped.

## Sources

- https://www.origincoffee.co.uk/
- https://www.origincoffee.co.uk/pages/story
- https://www.origincoffee.co.uk/pages/shipping
- https://www.origincoffee.co.uk/pages/b-corp-certified-coffee-roasters
- https://www.origincoffee.co.uk/pages/direct-trade
- https://www.origincoffee.co.uk/pages/sustainability
- https://www.origincoffee.co.uk/pages/origin-coffee-the-roastery
- https://www.origincoffee.co.uk/blogs/journal/sail-ship-coffee