---
type: "Reference"
title: "Phil & Sebastian Coffee Roasters — Roaster Profile"
description: "Calgary specialty coffee roaster with a Shopify coffee collection and an international-facing online catalogue."
---

# Phil & Sebastian Coffee Roasters — Roaster Profile

## Overview

Phil & Sebastian Coffee Roasters is a specialty roaster based in Calgary,
Alberta, Canada. The registered scraper targets the site's coffee collection;
the storefront is Shopify and the registered shop display is in GBP. The site
was rate-limited during this research, so unsupported equipment, sourcing and
shipping details are intentionally omitted.

## Address

- Calgary, Alberta, Canada — full roastery address not published on the
  consulted site pages.

## Scraping Quirks

- The collection extractor accepts both ordinary Shopify `/products/` links and
  `/collections/coffee/products/` links, then excludes handles containing
  `instant-coffee`, `intro-` or `class-`. Product-card-specific selectors are
  included because the collection uses more than one link structure.

## Sources

- https://philsebastian.com
- https://philsebastian.com/collections/coffee
