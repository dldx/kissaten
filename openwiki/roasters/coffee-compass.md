---
type: "Reference"
title: "Coffee Compass — Roaster Profile"
description: "Family-run UK gourmet coffee roaster on the South Coast of England (Littlehampton, West Sussex) on Shopify, roasting on site to order with a four-collection catalogue of single origins, specialty blends, espresso and decaf."
---

# Coffee Compass — Roaster Profile

## Overview

Coffee Compass is a family-run, UK gourmet coffee roaster on the South Coast
of England, on a Shopify storefront at www.coffeecompass.co.uk. Its nav
organises the bean catalogue into four curated collections — single origins
(by region), specialty blends (Light/Medium, Mahogany, Extra Dark Ebony),
espresso range and decaf — totalling ~53 live products, and it roasts on site
to order. It also sells green (unroasted) beans, tea, gifts & trial packs and
runs a monthly "Coffee Club" subscription.

## Address

- Fort Road E, Wick, Littlehampton, West Sussex BN17 7QZ — United Kingdom

## Sourcing & Transparency

- Beans are sourced from farms and mills "personally selected for the best in
  their region", with an emphasis on agronomy, environmental impact and
  welfare of employees (per their site).
- Several lots are bought from women's cooperatives (e.g. Honduras Gea Diosa
  de la Tierra Women's Cooperative, Colombia FNC Santa Marta Women's
  Cooperative).

## Schedules & Shipping

- Roasted on site to order; despatched by courier, often the next day.
- "Next Day Delivery Mon–Fri before 1pm" (per their site).

## Philosophy & Quirks

- Coffee Club: a monthly subscription pack of their pick of the range; also
  random roast packs and trial ranges to explore new coffees.
- Decafs decaffeinated with natural techniques (Swiss Water / CO2).

## Scraping Quirks

- Shopify with a 4-collection merge (`roasted-origin-coffee`,
  `specialty-blends`, `espresso-range`, `decaf`); `collections.json`
  over-reports counts (e.g. 65 for single origins) because it counts
  unpublished items, while the effective union from `products.json` is ~53.
- The bare domain 301-redirects to www (Shopify canonical-host redirect); the
  scraper uses the www host.
- Canonical product URLs are `/products/<handle>` (no collection segment).
- `coffee-compass-gift-pack` and `coffee-compass-espresso-selection` are
  multi-bag samplers flagged `is_tasting_kit` / `requires_review` so they flow
  through the review queue, not public search.

## Sources

- https://www.coffeecompass.co.uk
- https://www.coffeecompass.co.uk/pages/about-us
- https://www.coffeecompass.co.uk/pages/contact-us