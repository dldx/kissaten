---
type: "Reference"
title: "Blue Hour Coffee — Roaster Profile"
description: "Winchester (Hampshire) speciality coffee roaster on Squarespace selling espresso and filter beans in 250g and 1kg with grind options, a Sunset Decaf Brazil, cacao and subscriptions — 'Roasted in Winchester'."
---

# Blue Hour Coffee — Roaster Profile

## Overview

Blue Hour Coffee is a Winchester (Hampshire) speciality coffee roaster running a
Squarespace storefront. It sells espresso and filter beans in 250g and 1kg bags
with grind options (including V60 / Aeropress / French Press / Whole Bean), a
decaf (Sunset Decaf Brazil), cacao and subscriptions. It describes itself as
"Roasted in Winchester".

## Address

- Winchester, Hampshire — United Kingdom (full street address not published on
  the site).

## Scraping Quirks

- Squarespace store (no products.json); product pages live under
  `/shop-coffee/p/<slug>`.
- Listing pages render products as JSON in a `.product-list` `data-context`
  attribute (no `<a href>` product links), which the scraper parses.
- Subscriptions (under `/subscriptions-1/p/`), cacao, bundles and gift cards are
  excluded.
- Product pages are large (~900KB) — the scraper compacts them to meta +
  static-context variants.

## Sources

- https://www.bluehourcoffee.co.uk
- https://www.bluehourcoffee.co.uk/shop-coffee