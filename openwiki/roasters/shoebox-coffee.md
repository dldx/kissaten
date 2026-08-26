---
type: "Reference"
title: "Shoebox Coffee — Roaster Profile"
description: "US specialty roaster focused on microlots and advanced fermentations, catalogued through current and archive Shopify collections."
---

# Shoebox Coffee — Roaster Profile

## Overview

Shoebox Coffee is a US specialty roaster focused on high-quality microlots and advanced fermentations. Its Shopify storefront exposes both coffee and archive collections. Direct site pages were rate-limited (HTTP 429) during this research pass, so no unsupported address, machine, sustainability or shipping details are recorded.

## Address

- United States — full roastery address, including town, was not published on the consulted pages.

## Scraping Quirks

- The scraper reads both `/collections/coffee/products.json` and `/collections/archive/products.json`, does not fetch individual product pages, and does not use optimised extraction.
- It rewrites collection URLs to the root `/products/<handle>` form. It excludes gift cards, wholesale, subscriptions, seasoning beans and products whose handles end in `-cup`.

## Sources

- https://shoebox.coffee
