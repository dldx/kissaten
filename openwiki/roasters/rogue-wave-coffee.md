---
type: "Reference"
title: "Rogue Wave Coffee — Roaster Profile"
description: "Edmonton specialty roaster known for single-origin coffees and unusual processing, with a Shopify coffee catalogue."
---

# Rogue Wave Coffee — Roaster Profile

## Overview

Rogue Wave Coffee is a Canadian specialty roaster based in Edmonton, offering single origins and coffees with distinctive processing methods. Its registered storefront is roguewavecoffee.ca. Direct site pages were rate-limited (HTTP 429) during this research pass, so equipment, sustainability, shipping and price-transparency claims are omitted rather than inferred.

## Address

- Edmonton, Alberta, Canada — full roastery street address was not published on the consulted pages.

## Scraping Quirks

- The scraper consumes the Shopify `coffee` collection's `products.json` endpoint and normalises collection product URLs to `/products/<handle>`.
- It restricts extraction to the product-information wrapper on product pages and excludes surprise offerings, the MHW/Origami/Kettle/Brewista equipment range, subscriptions, gifts, wholesale, accessories and ceramics.

## Sources

- https://roguewavecoffee.ca
