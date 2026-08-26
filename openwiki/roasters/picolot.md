---
type: "Reference"
title: "Picolot — Roaster Profile"
description: "US micro-roaster built around tiny lots and limited seasonal releases, with a Season 2 collection and archived Season 1 coffees."
---

# Picolot — Roaster Profile

## Overview

Picolot is a United States coffee business whose storefront describes its offer as a curation of extremely tiny lots and interesting beans. The Shopify shop is organised around a current “Season 2” collection and an archive of “Season 1” coffees. The site also offers a founding membership and special releases.

## Address

- United States — full roastery address not published on site.

## Schedules & Shipping

- The storefront banner states: free US shipping on orders of $50 or more; Canada shipping is available. No other destination-specific rates were published in the fetched storefront.

## Scraping Quirks

- The scraper fetches both the main `products.json` endpoint and the `coffee-archive` collection, then canonicalises collection product URLs to `/products/<handle>` so current and archived entries deduplicate.
- Bag weight is taken from `Quantity:` or `Bag Size:` in `body_html`, not Shopify’s variant `grams` field, which the scraper documents as unreliable; only values from 15–2000 g are accepted.
- Equipment, gifts, bundles, memberships, and other non-coffee slugs are excluded by explicit slug fragments.

## Sources

- https://picolot.shop
- https://picolot.shop/collections/our-collection
- https://picolot.shop/collections/coffee-archive
