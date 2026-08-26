---
type: "Reference"
title: "Market Lane Coffee — Roaster Profile"
description: "Melbourne specialty roaster and café group built around seasonal coffees and a coffee-only product archive."
---

# Market Lane Coffee — Roaster Profile

## Overview

Market Lane Coffee is a specialty coffee roaster based in Melbourne, Australia. The registered scraper targets the roaster’s `/pages/coffee` coffee page and the brand’s Shopify product URLs. The site was rate-limited during this research pass, so founding, sourcing, equipment, shipping, and precise roastery-address claims are not added here without a directly verified page.

## Address

- Melbourne, Victoria, Australia — full roastery address not published on the pages available during this research pass.

## Scraping Quirks

- The registry key is `market-lane-coffee`. The scraper collects links containing `/products/` from the coffee page, but the local `excluded_patterns` variable is empty even though `_get_excluded_url_patterns()` lists bundle, gift-card, accessories, coffee-drip-bags, and tea patterns. Future contributors should verify whether non-coffee links can therefore enter the catalogue.

## Sources

- https://marketlane.com.au
- https://marketlane.com.au/pages/coffee
