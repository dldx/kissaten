---
type: "Reference"
title: "Passage Coffee — Roaster Profile"
description: "Mitaka, Tokyo specialty roaster offering Japanese and English coffee shop catalogues."
---

# Passage Coffee — Roaster Profile

## Overview

Passage Coffee is a specialty roaster based in Mitaka, Tokyo, Japan. The
registered scraper targets its English-language beans collection on a Shopify
store and uses product pages because the descriptions require translation.
Further sourcing, equipment and fulfilment claims are omitted because the site
was rate-limited during this research.

## Address

- Mitaka, Tokyo, Japan — full roastery address not published on the consulted
  site pages.

## Scraping Quirks

- The scraper consumes the English `products.json` collection, caches product
  pages and always translates extracted content to English. Before extraction it
  removes the product-recommendations carousel and narrows the HTML to
  `div.product-full-width` when present.

## Sources

- https://passagecoffee.com
- https://passagecoffee.com/en/collections/beans/products.json
