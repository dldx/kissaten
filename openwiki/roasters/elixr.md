---
type: "Reference"
title: "Elixr Coffee Roaster — Roaster Profile"
description: "Philadelphia specialty coffee roaster with a Shopify storefront and a tightly filtered coffee collection."
---

# Elixr Coffee Roaster — Roaster Profile

## Overview

Elixr Coffee Roaster is a specialty coffee roaster based in Philadelphia,
United States. Its Shopify storefront sells coffee in USD and the registered
scraper uses the `elixr` collection. The site also carries non-coffee goods and
services, so the scraper applies a deliberate product filter.

## Address

- Philadelphia, Pennsylvania, United States — full roastery street address not published on site.

## Scraping Quirks

- Product discovery uses several Shopify card selectors and Playwright before
  AI extraction.
- The scraper excludes subscriptions, gifts, wholesale, equipment,
  accessories, merchandise, apparel, matcha, tumblers and other named
  non-bean handles. It also excludes the generic `treehouse` handle because
  the origin is not specific enough; that is a genuine Elixr-specific rule.

## Sources

- https://elixrcoffee.com
- https://elixrcoffee.com/collections/elixr
