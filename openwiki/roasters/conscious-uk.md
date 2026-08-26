---
type: "Reference"
title: "Conscious Coffee (UK) — Roaster Profile"
description: "Conscious (consciousspeciality.com) is an independent UK specialty coffee roaster on a Webflow Ecommerce storefront selling single origins, blends and a decaf in GBP, with producer-level price transparency."
---

# Conscious (UK) — Roaster Profile

## Overview

Conscious (consciousspeciality.com — canonical non-www; trading as Conscious
with Coffee Roasters Ltd) is an independent UK specialty coffee roaster on a
**Webflow Ecommerce** storefront, selling whole-bean single origins, espresso /
filter / allrounder blends and a decaf, priced in GBP. The team (Culainn and
Lea) began working alongside coffee producers in South America in 2021 and
partners with smallholder producers and community projects, mainly in Peru,
Bolivia and Colombia, publishing producer price-transparency (£/KG) on product
pages. It is the successor to the dead `consciouscoffee.co.uk` and is a
**distinct company** from the US Boulder, Colorado Conscious Coffees
(consciouscoffees.com), which Kissaten tracks as a separate "guest" roaster.

## Address

- United Kingdom — the site publishes no town, county or street address (only
  a UK company number); full roastery address not published on site.

## Scraping Quirks

- **Webflow Ecommerce**, not Shopify: there is no `products.json` / WooCommerce
  `wp-json`. Prices/currency ship in a `window.__WEBFLOW_CURRENCY_SETTINGS`
  blob (`currencyCode: GBP`); the scraper pins `currency="GBP"` defensively.
- **Sitemap discovery**: the Webflow `/category/*` pages render only a small
  subset with no pagination links, so the static `/sitemap.xml` (one `/product/<slug>`
  URL per product) is the authoritative enumeration source.
- The `conscious-uk` registry slug (data dir `conscious_coffee/`, shared with
  the US entity) is the UK entity at consciousspeciality.com — **distinct from
  the US `conscious-coffee` guest** at consciouscoffees.com (Boulder, CO, USD).
- The 29 remaining sitemap products are whole-bean coffees; the four non-coffee
  entries (a `conscious-choice-subscription` and `hario-v60-*` equipment) are
  dropped by the base exclude patterns, and no tasting-kit product is flagged
  for review.

## Sources

- https://consciousspeciality.com
- https://consciousspeciality.com/about
- https://consciousspeciality.com/contact
- https://consciousspeciality.com/sitemap.xml