---
type: "Reference"
title: "Nokora — Roaster Profile"
description: "Bilbao specialty-coffee business presenting a Shopify catalogue of coffees and a city tasting shop."
---

# Nokora — Roaster Profile

## Overview

Nokora Coffee is a specialty-coffee business based in Bilbao, Spain, with a
Shopify storefront. Its catalogue is centred on coffees in the “Cafés”
collection, alongside a gift card and a tasting shop; the site presents Nokora
as a way to explore the identity of specialty coffee. The reviewed homepage
does not publish a founding year or roasting-machine details.

## Address

- Bilbao, Spain — the published Plaza del Museo address is identified as the
  tasting-shop location, not explicitly as the roastery; full roastery address
  not published on site.

## Schedules & Shipping

- The homepage advertises collection in store or shipping to mainland Spain and
  free shipping from EUR 50. No public roast cadence, dispatch day or
  destination-specific rate was found on the reviewed official pages.

## Scraping Quirks

- The scraper uses the `/collections/cafes` collection, selects the theme’s
  product-grid card links, and checks the parent card for `div.price--sold-out`
  before accepting a product. AI extraction translates the product data to
  English; there are currently no additional URL exclusion patterns.

## Sources

- https://nokora.coffee
- https://nokora.coffee/collections/cafes
