---
type: "Reference"
title: "DAK Coffee Roasters — Roaster Profile"
description: "Amsterdam specialty coffee roaster with an API-backed coffee catalogue and a focus on contemporary Dutch specialty coffee."
---

# DAK Coffee Roasters — Roaster Profile

## Overview

DAK Coffee Roasters is a Dutch specialty coffee roaster based in Amsterdam,
per the registered declaration. Its current storefront is
`dakcoffeeroasters.com`; the reviewed storefront requires JavaScript, so no
additional official-page claims are made here.

## Address

- Roastery: Amsterdam, Netherlands — full address not published on the reviewed official pages.

## Scraping Quirks

- Unlike the other assigned shop scrapers, DAK uses the site's
  `api/products/all?isActive=true` endpoint rather than an HTML collection or
  Shopify `products.json` endpoint.
- Only API records whose `type` is exactly `coffee` are processed. Product URLs
  are constructed as `/shop/coffee/<slug>`; existing products are handled via
  diffjson stock updates unless a full update is requested.

## Sources

- https://www.dakcoffeeroasters.com
- https://www.dakcoffeeroasters.com/api/products/all?isActive=true
