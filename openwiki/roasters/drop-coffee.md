---
type: "Reference"
title: "Drop Coffee — Roaster Profile"
description: "Stockholm specialty coffee roaster focused on sweetness, clarity and vibrancy, with a Shopify bean collection and a tasting-pack exclusion in Kissaten."
---

# Drop Coffee — Roaster Profile

## Overview

Drop Coffee Roasters is a Swedish specialty coffee roaster based in Stockholm.
The shop is Shopify-based and sells coffee in SEK. The company describes its
coffee focus as sweetness, clarity and vibrancy (per the scraper's registered
declaration); the storefront's bean collection is the source for the public
coffee catalogue.

## Address

- Stockholm, Sweden — full roastery street address not published on site.

## Scraping Quirks

- The scraper uses the bean collection and Playwright because the collection
  page is rendered dynamically.
- `drop-coffee-tasting-pack`, `little-drop-single-brew-kit` and
  `advent-kalender` are explicitly excluded. Future changes should preserve
  this product-level rule rather than excluding sampler products generically.

## Sources

- https://dropcoffee.com
- https://www.dropcoffee.com/collections/beans
