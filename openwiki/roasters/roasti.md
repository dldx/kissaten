---
type: "Reference"
title: "Roasti Coffee Co. — Roaster Profile"
description: "Sherwood Park, Alberta roaster and coffee bar serving direct-sourced single origins and blends, with a Fazenda Samambaia (Brazil) sourcing story and Classic/Exotic sampler packs"
---

# Roasti Coffee Co.

## Overview

Roasti Coffee Co. is a specialty coffee roaster operating a roastery and coffee
bar in Sherwood Park, Alberta, Canada (Edmonton area). Their storefront is a
Shopify shop selling single origins (Colombia Paraiso Red Bourbon, Ethiopia
Shantawene, Guatemala Los Volcanes, Brazil Yellow Bourbon), an
Espresso Blend (Brazil x Guatemala), a Colombian sugarcane decaf, instant
coffee packets, and curated Classic/Exotic sampler packs and taster boxes.
Their "Sourcing" page is dedicated to Fazenda Samambaia, the Brazilian farm
that grows their Brazil coffee.

## Address

- #19, 52 Brentwood Blvd, Sherwood Park, AB T8A 2H6, Canada (per their site — roastery & coffee bar)

## Sustainability

- Rainforest Alliance and UTZ certifications at Fazenda Samambaia, their
  spotlighted Brazilian partner farm (Carmo de Minas, Minas Gerais — 50 ha of
  coffee, 30 ha preserved, raised-bed drying, per their sourcing page).

## Sourcing & Transparency

- They buy either directly from producers and cooperatives or from reputable
  brokers based in Alberta and Quebec who maintain long-term relationships in
  producing countries; producers are paid a premium for higher-quality crops
  with open dialogue to ensure production costs are covered (per their site).
- They state a focus on transparency "so everyone knows who gets what across
  the whole supply chain" (per their site); no per-bag FOB/farm-gate figures
  are published.

## Schedules & Shipping

- Free local delivery Monday–Friday on orders over CAD $30 (Spruce Grove, St.
  Albert, Leduc and Devon on Wednesdays; order cut-off midnight the day
  before delivery) — per their site.
- Canada-wide shipping is offered; mail-out orders ship within 24–48 hours,
  with no shipping or deliveries on weekends or statutory holidays (per their
  shipping policy). No per-region shipping rates are published.

## Philosophy & Quirks

- The flagship sourcing story is Fazenda Samambaia, the Cambraia family farm
  in Carmo de Minas: Henrique Dias Cambraia took over at age 20 in 1993 after
  his father's death and pivoted the estate to specialty coffee in 1997
  (per their site).
- Product URLs carry a Shopify copy artifact — the dark-roast Brazil is
  published under the handle `copy-of-brazil-dark-direct-trade` — a leftover
  of duplicating an earlier product in the Shopify admin.
- Individual product pages list notes, origin, producer, process, altitude
  and variety in the description; coffee is sold in 227g / 2lb / 4oz sample
  sizes, each with a choice of six grind types (whole bean through AeroPress).

## Scraping Quirks

- The curated `coffee-beans` collection contains everything coffee-related —
  single origins, blends, decaf, instant packets and the Classic/Exotic
  samplers plus taster boxes — so the scraper uses no slug exclusions. The
  sampler/taster products intentionally flow through the tasting-kit review
  queue (`is_tasting_kit` / `requires_review`) rather than being dropped.
- The site canonicalizes product pages to `/products/<handle>` (no collection
  segment), so the scraper strips the `/collections/coffee-beans` prefix from
  products.json-derived URLs.
- `store_currency` is pinned to CAD (the store serves Canada | CAD by
  default) to guard against geo-converted prices from a datacenter IP.

## Sources

- https://roasti.ca/
- https://roasti.ca/pages/about
- https://roasti.ca/pages/fazenda-samambaia
- https://roasti.ca/pages/shipping
- https://roasti.ca/policies/shipping-policy
- https://roasti.ca/collections/coffee-beans/products.json
