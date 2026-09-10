---
type: "Reference"
title: "Feri — Roaster Profile"
description: "London micro-roaster whose story began home-roasting in Hong Kong's Ferry Point in 2014 — Wednesday roast days, Gesha Village rarities and a 'sold out means gone' discovery collection."
---

# Feri — Roaster Profile

## Overview

feri. coffee is a small London-based roaster selling through a WooCommerce
storefront at [feripoint.com](https://feripoint.com) and via select cafés
across London. The project began in Hong Kong in 2014 with small-batch
roasting at home in **Ferry Point** — the origin of the name — before moving
to London in 2020, where feri. coffee was born. The catalogue leans towards
rare and distinctive lots: Ethiopia Gesha Village, Panama Altieri Geisha,
Colombia SL28, and coffees from China.

## Address

- London — United Kingdom (full address not published on site)

## Roasting & Equipment

- No roasting machine is named on the site; roasting is described as guided
  by "experience and close observation of time and temperature rather than
  heavy automation".
- Favours **lighter profiles** for clarity and vibrancy, adjusted per coffee
  and per café partner; the aim is "balance, sweetness, and structure — never
  excess".
- Small-batch development and production, London-based.

## Schedules & Shipping

- **Roast day is Wednesday.** Orders placed after 21:00 on Tuesday roll into
  the following week's roast cycle.
- Fulfilment via **Royal Mail and DPD**; estimated delivery 3–10 working days
  (typically 2–5).
- **Free UK shipping on coffee orders over £30**; flat **£3.65** for smaller
  orders.
- Selected European cities: shipping rates calculated at checkout; other
  international destinations by quote (order@feripoint.com).

## Philosophy & Quirks

- "Coffee is shaped by attention and experience rather than trends or
  technology alone" — clarity, balance, and respect for each coffee's natural
  character.
- The name **feri** comes from **Ferry Point**, the Hong Kong neighbourhood
  where the founder started home-roasting in 2014.
- Sourcing spans Ethiopia, Kenya, Panama and China, spanning both classic and
  progressive processing; rare micro-lots are sold in small formats (e.g.
  Panama Chiriquí Altieri Geisha in 80g bags).
- Limited coffees appear in the **Discovery Collection** — per their site,
  once a coffee is sold out it will not return.
- Also offers professional roasting services: roast profiling, house blend
  development and white-label roasting for cafés and coffee brands.

## Scraping Quirks

- **Card-scoped sold-out filtering**: out-of-stock detection ("Out of stock"/
  "Sold out" text or `outofstock` class) is applied per product card and runs
  before the coffee-URL check. A page-wide text search would false-positive
  on marketing copy such as "Once sold out, they will not return" on the
  discovery collection page.
- **Elementor fallback**: the Elementor-driven discovery collection page links
  products from marketing blocks that are not wrapped in WooCommerce product
  cards, so the scraper falls back to bare `/product/` links (still filtered
  through the coffee-URL check).

## Sources

- https://feripoint.com/
- https://feripoint.com/my-story/
- https://feripoint.com/shipping-policy/
- https://feripoint.com/service-page/
