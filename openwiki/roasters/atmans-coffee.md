---
type: "Reference"
title: "atmans Coffee — Roaster Profile"
description: "Barcelona specialty roaster with a curated Shopify coffee range and a stated focus on POV."
---

# atmans Coffee — Roaster Profile

## Overview

atmans Coffee is a specialty coffee roaster based in Barcelona, Spain. Its
Shopify storefront uses an English path for the “all coffees” collection and
also offers other shop products. The official pages accessible during research
did not publish a verifiable roastery street address, roasting hardware,
sustainability programme or fulfilment schedule.

## Address

- Barcelona — Spain; full roastery address not published on the accessible site pages.

## Scraping Quirks

- The scraper reads `/en/collections/all-coffees/products.json`, scrapes product
  pages, and narrows AI extraction to the `<product-form>` element when present.
- It excludes `pack-de-muestras`, `beanz`, `coffee-bag` and `suscripcion-`
  handles. The AI override always translates extracted content to English.

## Sources

- https://www.atmanscoffee.com
- https://www.atmanscoffee.com/en/collections/all-coffees
