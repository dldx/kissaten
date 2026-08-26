---
type: "Reference"
title: "Coffee Collective — Roaster Profile"
description: "Copenhagen, Denmark specialty roaster built around direct relationships with coffee producers and seasonal filter and espresso coffees."
---

# Coffee Collective — Roaster Profile

## Overview

Coffee Collective is a Copenhagen-based Danish specialty coffee roaster. The
registered scraper describes its focus as direct-trade relationships with
farmers and uses the roaster's Shopify storefront. Coffee Collective's full
roastery street address was not confirmed in the reviewed official pages.

## Address

- Roastery: Copenhagen, Denmark — full address not published on the reviewed official pages.

## Sourcing & Transparency

- The registered description identifies direct trade with farmers as the
  roaster's sourcing focus. No price-paid-to-producer or cost-breakdown figures
  were verified in the reviewed material.

## Scraping Quirks

- The scraper merges the filter-coffee and espresso `products.json` collections
  and canonicalises product URLs to `/products/<handle>` when a collection path
  is present.
- It sends the `div.about-this-section` product fragment to the AI extractor when
  that element exists, and excludes advent calendars, gift cards, subscriptions,
  workshops, equipment and merchandise.

## Sources

- https://coffeecollective.dk
- https://coffeecollective.dk/collections/filter-coffee/products.json
- https://coffeecollective.dk/collections/espresso/products.json
