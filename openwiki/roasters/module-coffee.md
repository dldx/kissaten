---
type: "Reference"
title: "Module Coffee — Roaster Profile"
description: "Edinburgh limited-release micro-roaster (launched 2025) roasting renowned lots on a Loring S7 Nighthawk — numbered M-series boxes that sell out and pave the way for the next release."
---

# Module Coffee — Roaster Profile

## Overview

Module (styled **MODULE**) is a deliberately small Edinburgh roastery launched in
2025 after a decade of running a multi-roaster café, focused on "the modern
roasting of renowned lots". Rather than a standing catalogue it works on a
sequential limited-release model: each coffee is a numbered box in an ongoing
series (M15, M17, M18 …), and once a release sells out it paves the way for the
next. Releases are named for the producer or farm (La Palma Y El Tucán, Juan
Peña, Finca Lérida, Bambito Estate…). The custom storefront lives at
[module-roast.com](https://module-roast.com).

## Address

- Edinburgh, Scotland — United Kingdom (all coffee is roasted offsite; full
  roastery address not published on site). Free collection is offered from
  **Lowdown, 40 George Street, Edinburgh EH2 2LE**, the founders' café.

## Roasting & Equipment

- **Loring S7 Nighthawk** hot-air roaster, chosen for precise control
  throughout the roast; each coffee gets its own profile.
- A **CM100+ Colour Meter** plus sensory evaluation is used to measure roast
  colour and keep consistency from one release to the next.

## Schedules & Shipping

- Coffee is roasted within a week of ordering; orders are packed and
  dispatched within 48 hours of purchase (excluding bank holidays).
- UK only, via Royal Mail Tracked 48. Tiered rates per their site:
  1–5 boxes **£4.75**, 6–14 boxes **£8.00**, 15–25 boxes **£12.00**. No
  free-delivery threshold; free collection from Lowdown instead.
- International orders by email enquiry.

## Philosophy & Quirks

- Everything is framed as an ongoing exploration: "each release building on
  the previous in the series, making every box an individual experience."
- The "award winning" packaging is treated as part of the release itself —
  minimalist rigid-box design with its own identity per release (press
  coverage, e.g. The Dieline, has highlighted it).
- Wholesale is deliberately small: independent cafés, restaurants and
  specialist retailers, plus a wholesale page for new partners.

## Scraping Quirks

- **Limited-release catalogue rotation**: products are numbered releases
  (e.g. `/shop/m15/`) that sell out and are replaced, so the catalogue churns
  constantly; the scraper fetches the shop with
  `?filter.v.availability=1` and drops non-coffee items
  (`gift-card`, `tote-bag`, `subscription`).
- **AI-powered extraction with DOM narrowing**: product pages go through a
  custom `fetch_page` that trims the `/shop/m/*` page down to the
  product-info container before AI extraction.

## Sources

- https://module-roast.com/
- https://module-roast.com/info/
- https://module-roast.com/shipping/
- https://module-roast.com/shop/
- https://dayglow.coffee/blogs/stories/a-taste-of-scotland-with-module-roast
