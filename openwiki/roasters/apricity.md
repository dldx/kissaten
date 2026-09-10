---
type: "Reference"
title: "Apricity — Roaster Profile"
description: "Founder-led specialty roastery in Prestatyn, North Wales — exclusive producer lots like Edinson Argote's pineapple co-ferment, an 'Apricity Spectrum' flavour framework, and a brew bar at the roastery."
---

# Apricity — Roaster Profile

## Overview

Apricity is a founder-led independent specialty coffee roastery based in
Prestatyn, North Wales (United Kingdom), with a brew bar on site at the
business park roastery. The founder describes building the roastery "after a
decade" in a community that shaped their standards; no founding year is
published on the site. The storefront is Shopify at
[apricitycoffee.co.uk](https://apricitycoffee.co.uk). The catalogue leans on
close producer relationships — e.g. a pineapple co-ferment from Edinson
Argote's Quebraditas farm produced exclusively for Apricity, alongside
flavour-forward releases like Caramel Crème, Watermelon Slice and Ají Orange.

## Address

- Apricity Coffee LTD, Unit 18 Prestatyn Business Park, Warren Drive,
  Prestatyn, LL19 7HT, Wales — United Kingdom

## Sustainability

- All packaging is fully recyclable, with materials chosen to minimise waste
  (per their shipping policy).
- The site publishes a "Sustainable Approach" promise — responsible and
  transparent sourcing — but no named programmes.

## Schedules & Shipping

- Roasts and dispatches on a set day each week; the current day is shown on
  the website and orders after the weekly cut-off roll to the next roast day.
- UK: Royal Mail 1st Class (1–2 working days) or 2nd Class (2–4 working days).
- International: Royal Mail International; delivery times vary by country and
  customers are liable for customs duties/import fees.
- No free-delivery threshold is published on the site.

## Philosophy & Quirks

- Three stated values: **Care Before Commerce**, **Connection is the Point**,
  **Integrity in Everything** — "Quality over quantity. Humanity over haste.
  Transparency over trend."
- **The Apricity Spectrum** — a house framework that guides drinkers "from
  familiar and comforting to rare and expressive" across process and origin.
- Producer-exclusive lots are a signature: Edinson Argote's Quebraditas
  pineapple co-ferment ("Pineapple Cake") is roasted for Apricity alone, with
  restocks announced via email and socials.

## Scraping Quirks

- **Bean details live in accordions**: origin/process/variety/tasting notes
  are hidden inside collapsible `div.product__accordion` sections, so the
  scraper filters the product page down to just those accordions before AI
  extraction.
- Collection URLs (`/collections/all-coffees/products/<slug>`) are normalised
  to canonical top-level `/products/<slug>` URLs.
- Wholesale `*-3kg` bags and equipment/merch (Timemore, V60, Fellow Atmos,
  tees, subscription/gift cards) are excluded by slug.

## Sources

- https://apricitycoffee.co.uk/
- https://apricitycoffee.co.uk/pages/our-story
- https://apricitycoffee.co.uk/pages/brew-bar
- https://apricitycoffee.co.uk/pages/sourcing
- https://apricitycoffee.co.uk/policies/shipping-policy
- https://apricitycoffee.co.uk/pages/contact