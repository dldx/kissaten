---
type: "Reference"
title: "Sey Coffee — Roaster Profile"
description: "Brooklyn specialty roaster recognised for detailed producer partnerships and price transparency."
---

# Sey Coffee — Roaster Profile

## Overview

Sey Coffee is a Brooklyn-based specialty coffee roaster known for exceptional sourcing, detailed producer partnerships and price transparency. Its Shopify shop carries current coffees through a coffee collection. Direct Sey pages were rate-limited (HTTP 429) during this research pass, so specific current transparency figures, hardware and shipping terms are not reproduced here.

## Address

- Brooklyn, New York, United States — full roastery street address was not published on the consulted pages.

## Scraping Quirks

- The scraper intentionally reads the current coffee collection only; the archived-coffees `products.json` endpoint is present in code but commented out.
- It canonicalises every product to `https://www.seycoffee.com/products/<slug>`, checks both canonical and source URL against historical data to avoid duplicates, and marks archived-collection products out of stock if they are later enabled.
- Non-coffee items, recurring products, test roasts, gifts, wholesale, equipment, accessories and merchandise are excluded by slug.

## Sources

- https://www.seycoffee.com
