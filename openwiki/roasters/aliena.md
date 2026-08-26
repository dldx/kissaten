---
type: "Reference"
title: "Aliena Coffee Roasters — Roaster Profile"
description: "Rome specialty roaster with a Shopify coffee range spanning single origins, blends and limited releases."
---

# Aliena Coffee Roasters — Roaster Profile

## Overview

Aliena Coffee Roasters is a specialty roaster based in Rome, Italy. Its
Shopify storefront is hosted at caffealiena.com and the registered coffee shop
range is collected under a front-page collection. The accessible catalogue
also includes non-coffee goods, so the profile represents the coffee scraper
rather than the whole shop.

## Address

- Rome — Italy; full roastery address not published on the accessible site pages.

## Scraping Quirks

- The scraper reads `collections/frontpage/products.json`, scrapes product
  pages with AI extraction, and removes the collection segment from URLs so
  canonical pages are used.
- Handles containing `cold-brew`, `gift-card` or `subscription` are excluded.

## Sources

- https://caffealiena.com
- https://caffealiena.com/collections/frontpage
