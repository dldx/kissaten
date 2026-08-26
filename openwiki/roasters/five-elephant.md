---
type: "Reference"
title: "Five Elephant — Roaster Profile"
description: "Berlin specialty coffee roaster with espresso, filter and special-lot collections in a Shopify storefront."
---

# Five Elephant — Roaster Profile

## Overview

Five Elephant is a specialty coffee roaster based in Berlin, Germany. Its
storefront is Shopify-based and sells coffee in EUR through separate espresso,
filter-bean and special-lot collections. The registered scraper treats those
three collections as the catalogue sources.

## Address

- Berlin, Germany — full roastery street address not published on site.

## Scraping Quirks

- The scraper expects a `.collection__products` grid and reads product links
  from that first grid; if the grid is absent it returns no products.
- Links whose parent text contains `Sold out` are skipped, and the resulting
  URLs are deduplicated with a set. There are currently no additional
  handle-exclusion patterns.

## Sources

- https://www.fiveelephant.com
- https://www.fiveelephant.com/collections/espresso
- https://www.fiveelephant.com/collections/filter-coffee-beans
- https://www.fiveelephant.com/collections/special-lots
