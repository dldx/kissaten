---
type: "Reference"
title: "The Angry Roaster — Roaster Profile"
description: "Burlington, Ontario roaster with a loud anti-establishment brand, weekend roast cycles and a small rotating menu of single-origins, a sugarcane-EA decaf and even a specialty instant coffee."
---

# The Angry Roaster — Roaster Profile

## Overview

The Angry Roaster (The Angry Roaster Coffee Co. / The Angry Roaster Inc.) is a
specialty coffee roaster based in Burlington, Ontario, Canada, selling through
a Shopify storefront. The brand leans into an intentionally loud, sweary,
anti-establishment voice ("if you're not angry, you're not awake"). The menu is
small and rotating — typically a half-dozen coffees including a house "Mad
House Roast" blend, single-origin lots from Colombia, Uganda, Papua New Guinea
and Kenya, a sugarcane-EA decaf processed from Wilton Benitez lots, and a
specialty instant coffee (Colombia Gesha Buesaco). Products are grouped into
playful roast-mood collections ("calm", "coffee-middle", "coffee-angry") and
the shop also sells brew gear (OREA brewers, SIBARIST filters, ICOSA/Avensi
glassware) and merch.

## Address

- 2531 Northampton Blvd, 2, Burlington ON L7M4H5, Canada (per their privacy
  policy; the site does not publish a separate roastery/visit address).

## Schedules & Shipping

- They roast on the weekend, per their shipping policy; available coffee ships
  same or next business day, otherwise after the next roast cycle.
- Free shipping on Canadian orders over **$65 CAD** (checkout banner: "Buy
  Canadian. Free shipping for orders over $65"). Per-region rate tables are
  not published on the policy pages checked.

## Philosophy & Quirks

- Founded out of 2020 frustration: the About page frames the brand as a
  response to that year's wildfires, pollution, politics and labour conditions,
  with a mission "to bridge the gap between the everyday unconscious coffee
  consumer and the speciality drinker, between farmer and roaster".
- Product names keep the bit going: "The Mad House Roast", "Piña Colada" and
  "Roasted Pears" flavoured-style lots, and collection names graded from
  "calm" to "angry" by roast intensity.
- Several coffees carry fair-trade tags and some organic certification tags
  (per product tags); no price-transparency figures are published.

## Scraping Quirks

- The store uses Shopify Markets geo-conversion: unpinned requests from a
  datacenter IP get US-converted prices (e.g. 16.28 instead of 22.00 CAD for
  The Mad House Roast). The scraper pins `country=CA` on every products.json
  request and locks `store_currency` to CAD.
- The curated `/collections/coffee` collection is used instead of
  `/collections/all` (which mixes in gear and merch). Two retail products
  (instant coffee, Uganda) carry a `wholesale` **tag** — harmless, since slug
  exclusion matches handles, not tags.
- Product pages are canonical at `/products/<handle>` while the products.json
  base builds `/collections/coffee/products/<handle>` URLs; the scraper strips
  the collection segment to match.

## Sources

- https://theangryroaster.com/
- https://theangryroaster.com/pages/about
- https://theangryroaster.com/collections/coffee
- https://theangryroaster.com/policies/shipping-policy
- https://theangryroaster.com/policies/privacy-policy
