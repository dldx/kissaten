---
type: "Reference"
title: "Blossom — Roaster Profile"
description: "UK specialty coffee roaster based in Cardiff, Wales, sourcing single-origin coffees from Colombia (Finca San Jose geisha, Las Peñas, Santa Elena, El Granadilla), Guatemala and beyond, roasted in small batches with a cost-transparency and producer-relationship focus."
---

# Blossom — Roaster Profile

## Overview

Blossom is a UK specialty coffee roaster based in Cardiff, Wales, sourcing
single-origin coffees from Colombia (Jaime Urrea Pizo / Finca San Jose geisha,
Las Peñas, Santa Elena, El Granadilla geisha), Guatemala and beyond. It roasts
in small batches with a transparency and producer-relationships focus, and
sells 8 coffee products priced in GBP on a Shopify storefront at
blossomcoffee.co.uk.

## Address

- Cardiff, Wales — United Kingdom (street address not published on site).

## Philosophy & Quirks

- Transparency: product pages carry cost-transparency data — FOB price per kg,
  volume purchased and importer.
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
- Geographic disambiguation: this is the UK/Cardiff roaster at
  blossomcoffee.co.uk, NOT the US "Blossom Coffee Roasters" (Vashon Island,
  Seattle) at blossomcoffeeroasters.com — that US store is out of scope for
  the UK catalogue.

## Sources

- https://blossomcoffee.co.uk
- https://blossomcoffee.co.uk/collections/coffee