---
type: "Reference"
title: "Coffee Wallas — Roaster Profile"
description: "Canadian specialty coffee roaster with a stated focus on Asian coffee origins and a Shopify coffee collection."
---

# Coffee Wallas — Roaster Profile

## Overview

Coffee Wallas is a Canadian specialty coffee roaster focused on Asian coffee
origins, per the registered declaration. Its shop uses Shopify and exposes a
front-page product collection; the city and roastery street address were not
confirmed in the reviewed official pages.

## Address

- Roastery: Canada — full address not published on the reviewed official pages.

## Scraping Quirks

- Product links are normalised from collection URLs to the canonical
  `/products/<handle>` form.
- The scraper searches Shopify image URLs for `label` or `website`, injects
  matching images into a hidden `coffee-label-images` block, downloads the label
  image and supplies it to the AI extractor. If that fails, it only falls back
  to a page screenshot in optimised mode.
- Gift cards, subscriptions, `will-it-blend-`, merchandise and wholesale
  products are excluded.

## Sources

- https://coffeewallas.com
- https://coffeewallas.com/collections/frontpage/products.json
