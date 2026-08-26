---
type: "Reference"
title: "Cat & Cloud — Roaster Profile"
description: "Santa Cruz coffee company founded by three friends around connection, hospitality, and craft, with a producer reinvestment programme and a roastery beside its Swift Street cafe."
---

# Cat & Cloud — Roaster Profile

## Overview

Cat & Cloud is a Santa Cruz, California coffee company founded by Jared Truby, Chris Baca, and Charles Jack. The business began with a web store and after-hours roasting before opening its first cafe in 2016; it moved the roastery into a larger Swift Street space in 2023 and added a larger roaster. Its current shop carries seasonal single origins, house blends such as The Answer and Night Shift, decaf, subscriptions, and merchandise.

## Address

- 719 Swift Street, Suite 56, Santa Cruz, CA 95060 - United States
- 3600 Portola Drive, Santa Cruz, CA 95062 - United States
- 10 Parade Street, Suite A, Aptos, CA 95003 - United States
- 725 Front Street, Santa Cruz, CA 95060 - United States

## Sourcing & Transparency

- The Best Friends Club is built around person-to-person relationships with specific farmers, a local liaison, and a yearly coffee buying plan. Cat & Cloud says USD 1 for every pound of Best Friends Club coffee sold is reinvested in producer lives and describes examples including medical care, fertilizer costs, and a producer's Magnolia-tree conservation project.

## Philosophy & Quirks

- The company's mission is to inspire connection by creating memorable experiences. Its stated values are Hospitality, Artistry, Ownership, Teamwork, and Actively Pursuing Better. The three owners bring different backgrounds: barista competition and education, coffee work in East Africa, and finance and operations.

## Scraping Quirks

- The Shopify scraper uses `collections/coffee/products.json` and product-page extraction, then narrows HTML to `div.product__info-container`, where Cat & Cloud keeps its Origin Info accordion and product metadata. It canonicalises collection URLs to `/products/<handle>` and explicitly pins extracted currency to USD because the site's localized storefront can otherwise resolve the registry name to a GBP fallback. Subscriptions, instant coffee, gifts, equipment, and merchandise are excluded by slug.

## Sources

- https://catandcloud.com/pages/about-us
- https://catandcloud.com/pages/locations
- https://catandcloud.com/pages/the-best-friends-club-initiative
- https://catandcloud.com
