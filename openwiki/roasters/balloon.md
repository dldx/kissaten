---
type: "Reference"
title: "Balloon Coffee Roasters — Roaster Profile"
description: "Zurich specialty roaster whose shop combines sustainable-coffee positioning with Swiss single-origin, espresso and filter releases."
---

# Balloon Coffee Roasters — Roaster Profile

## Overview

Balloon Coffee Roasters GmbH presents itself as a Swiss specialty roaster with coffee roasted in Zurich. Its Shopify storefront organises the range into filter, espresso and standout-selection coffees, alongside the Orbiter and New Moon blends. The site also provides separate wholesale, reseller, FAQ and roasting-schedule pages.

## Address

- Zurich, Switzerland — full roastery address not published on the consulted site pages.

## Philosophy & Quirks

- Balloon's public positioning is “sustainable coffee roasted in Zurich”, with a catalogue that distinguishes filter and espresso coffees and highlights seasonal single-origin releases.

## Scraping Quirks

- The scraper uses the `/collections/coffee/products.json` feed and trims each product page to the main product section plus the flavour marquee. The product template keeps hidden Alpine.js accordions and a `noscript` copy of the flavour profile, technical information and roasting schedule, while removing recommendations and other page furniture. It excludes equipment, subscriptions, gifts, apparel, capsules, pods and other non-coffee slugs, but does not exclude tasting kits by a generic rule.

## Sources

- https://balloon.coffee
- https://balloon.coffee/pages/about
- https://balloon.coffee/pages/roasting-schedule
- https://balloon.coffee/pages/faq
