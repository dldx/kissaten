---
type: "Reference"
title: "Datura Coffee — Roaster Profile"
description: "Paris micro-roastery centred on seasonal coffees and a small, curated Shopify catalogue."
---

# Datura Coffee — Roaster Profile

## Overview

Datura Coffee is a micro-roastery based in Paris, France, according to the
registered declaration. Its shop is `daturacoffee.com`; the official storefront
pages were rate-limited during review, so unsupported operational and sourcing
claims are intentionally omitted.

## Address

- Roastery: Paris, France — full address not published on the reviewed official pages.

## Scraping Quirks

- The scraper checks two pages of the `frontpage` collection, removes products
  whose surrounding markup says “Sold out”, deduplicates the resulting URLs,
  and uses the non-Playwright AI extraction path.
- It excludes subscriptions, merchandise, equipment, gifts and gift cards by
  URL token. Tasting-kit products are not named in this exclusion list.

## Sources

- https://daturacoffee.com
- https://daturacoffee.com/collections/frontpage
