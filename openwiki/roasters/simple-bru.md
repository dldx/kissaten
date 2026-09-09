---
type: "Reference"
title: "Simple Bru Coffee Co — Roaster Profile"
description: "Cape Town roaster and coffee-shop group focused on experimentally processed coffees, with a transparent sourcing partnership with the Colombian importer Sabores."
---

# Simple Bru Coffee Co

## Overview

Simple Bru Coffee Co (often shortened to SBCC) is a specialty coffee roaster and
coffee-shop group in Cape Town, South Africa, roasting since its inception in 2018.
The group runs cafés in the city (including SBCC Harrington on Harrington Street and
spots in Milnerton and Melkbosstrand) plus a dedicated roastery. Its house coffee is
The Alternative Blend, a three-bean African/South American blend, and the roastery
explicitly styles itself around roasting experimentally processed lots — coffees
fermented and cultured in unorthodox ways — particularly from Colombia. The webshop
is a WordPress/WooCommerce store; simplebru.app is a separate SimpleBru coffee-loyalty
platform site, not the shop.

## Address

- SBCC Roastery, Unit 15A, Platinum Junction, 4 School St, Marconi Beam, Cape Town, 7441, South Africa

## Sourcing & Transparency

Per their roastery page, Simple Bru positions the producer–roaster link as central to
specialty coffee: they source better coffees, "trade transparently", and aim to build
awareness around production. They describe a close partnership with Sabores, an
importer dealing directly with Colombian coffee farmers, through whom they buy
specialty-grade lots (many exclusive to them). Broader green-coffee purchases are
chosen to support "positive and sustainable importers and traders", with a stated goal
of eventually buying lots directly from individual farms.

## Philosophy & Quirks

The roastery splits its style into two sub-categories: experimentally processed
coffees (fermentation/culturing manipulated between harvest and drying, requiring
radically different roast profiles) and washed coffees — with the stated goal for
experimental lots of preserving as much sweetness as possible.

## Scraping Quirks

- WordPress runs with default (non-pretty) permalinks: product pages are
  `/?product=<slug>` and the shop archive is the "Shop" page `/?page_id=1400`
  (`/shop/` returns a 404). The top-level `/wp-json/` REST root is blocked (404),
  though `index.php?rest_route=/wc/store/v1/products` works.
- Catalogue was a single published coffee (The Alternative Blend) at scraper-authoring
  time; the scraper intentionally does not drop sampler/tasting-kit products so future
  kits flow through the review queue.

## Sources

- https://simplebrucoffee.co.za/ (home)
- https://simplebrucoffee.co.za/?page_id=1400 (Shop)
- https://simplebrucoffee.co.za/?page_id=536 (The Roastery)
- https://simplebrucoffee.co.za/?page_id=72 (Contact Us)
- https://simplebru.app/ (loyalty platform, verified as a separate site)
