---
type: "Reference"
title: "September Coffee — Roaster Profile"
description: "Canadian specialty coffee roaster with a Shopify coffee catalogue and a Canada/UK-localised product URL path."
---

# September Coffee — Roaster Profile

## Overview

September Coffee Company is a Canadian specialty coffee roaster. Its registered storefront is september.coffee, with the scraper using the English/UK-localised coffee collection. Direct site pages were rate-limited (HTTP 429) during this research pass; no equipment, sustainability, shipping or price-transparency claims are included without a directly verified source.

## Address

- Canada — full roastery address, including town, was not published on the consulted pages.

## Scraping Quirks

- The scraper reads `en-gb/collections/coffee/products.json` and rewrites Shopify collection URLs to `en-gb/products/<handle>` so the catalogue uses canonical localised product paths.
- It excludes test batches, subscriptions, gifts, wholesale, equipment, accessories and merchandise. Product-page caching is enabled and extraction uses the scraper's optimised mode.

## Sources

- https://september.coffee
