---
type: "Reference"
title: "Blossom — Roaster Profile"
description: "UK specialty coffee roaster based in Manchester, England, sourcing single-origin coffees from Colombia (Finca San Jose geisha, Las Peñas, Santa Elena, El Granadilla), Guatemala and beyond, roasted in small batches with a cost-transparency and producer-relationship focus."
---

# Blossom — Roaster Profile

## Overview

Blossom is a UK specialty coffee roaster based in Manchester, England, founded
in 2020. It sources single-origin coffees from Colombia (Jaime Urrea Pizo /
Finca San Jose geisha, Las Peñas, Santa Elena, El Granadilla geisha), Guatemala
and beyond, roasts in small batches on a Loring S35 with a transparency and
producer-relationships focus, and sells 8 coffee products priced in GBP on a
Shopify storefront at blossomcoffee.co.uk. Its About page theme: “Better
coffee, built on long-term commitment.”

## Address

- Manchester, England — United Kingdom (street address not published on site).

## Sourcing & Transparency

- Long-term relationship sourcing (per the About page): works with one supply
  chain in each origin and returns to it every harvest, prioritises meaningful
  volumes of producers’ main-harvest coffees, and aims to deepen existing
  relationships as it grows rather than continually adding new suppliers. The
  intended benefits: greater security and confidence in future demand for
  producers, plus the financial capacity to invest in their own businesses.
- The About page says Blossom openly reports what it pays.
- Product pages carry cost-transparency data — FOB price per kg, volume
  purchased and importer.

## Roasting & Equipment

- Roasts in Manchester on a Loring S35 (per the About page).
- Aim: present the clearest expression of each coffee’s natural
  characteristics; sees the roaster’s role as unlocking the coffee’s potential
  and showcasing producers’ work in the most thoughtful and considered way
  possible.

## Schedules & Shipping

- Site-wide announcement: free shipping on orders over £30.
- No roast or dispatch schedule is published on the site.

## Philosophy & Quirks

- Founding motivation (per the About page): when Blossom started, many of
  Manchester’s best cafés and restaurants were serving coffee roasted
  elsewhere; the ambition was a modern Manchester roastery that could stand
  alongside the coffee companies it most admired around the world.
- Site metadata describes the team as “a small, passionate team”.
- The site footer links out to World Coffee Research and 1% for the Planet
  (badge links; neither affiliation is explained on the page).
- Site-wide offer: save up to 15% by subscribing.
- Producer-relationship focus with named farms/communities — e.g. Finca San
  Jose at 2200 masl, and the San Jose Geisha, a Copa de Oro Western Winner.
- Mártir decaf available.

## Scraping Quirks

- The product JSON `body_html` and `product_type` fields are empty — bean
  detail (tasting notes, origin, producer/farm, process, altitude, blend
  breakdown, transparency) lives only in `<details>` accordions and
  `div.metafield-rich_text_field` blocks on the rendered page, so the scraper
  page-scrapes with `preprocess_product_soup` pruning to those selectors.
- Canonical product URLs are `/products/<handle>` (no collection segment).
- Geographic disambiguation: this is the UK/Manchester roaster at
  blossomcoffee.co.uk, NOT the US "Blossom Coffee Roasters" (Vashon Island,
  Seattle) at blossomcoffeeroasters.com — that US store is out of scope for
  the UK catalogue.

## Sources

- https://blossomcoffee.co.uk
- https://blossomcoffee.co.uk/collections/coffee
- https://blossomcoffee.co.uk/pages/about-us