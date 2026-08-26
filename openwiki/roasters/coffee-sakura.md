---
type: "Reference"
title: "Coffee Sakura — Roaster Profile"
description: "Japanese specialty coffee roaster whose English-language Shopify shop sells its coffee in a dedicated 200 g collection."
---

# Coffee Sakura — Roaster Profile

## Overview

Coffee Sakura is a specialty coffee roaster in Japan. Its registered shop is
the English-capable Shopify storefront at `shop.coffeesakura.co.jp`; the
roastery city and street address were not confirmed in the reviewed official
pages.

## Address

- Roastery: Japan — full address not published on the reviewed official pages.

## Scraping Quirks

- The scraper reads the dedicated `coffeebeans200g` Shopify collection rather
  than a general catalogue.
- It deliberately forces every Shopify variant to 200 g / 0.2 kg and then
  forces the extracted bean weight to 200 g. Japanese product content is always
  sent to the AI extractor with English translation enabled.
- Gift cards, subscriptions, workshops, tasting products, equipment and
  accessories are excluded by slug.

## Sources

- https://shop.coffeesakura.co.jp
- https://shop.coffeesakura.co.jp/collections/coffeebeans200g/products.json
