---
type: "Reference"
title: "Bear With Me Coffee — Roaster Profile"
description: "London (Wembley) UK coffee roaster on a Wix storefront selling single-origin coffees in 200g bags, easy-drip single-serve pouches, brew bags and subscriptions, plus an EASYDRIP Coffee Collection Mix&Match box — a family of coffee professionals behind the brand."
---

# Bear With Me Coffee — Roaster Profile

## Overview

Bear With Me Coffee is a UK coffee roaster at bearwithmecoffee.co.uk, a Wix
storefront based in Wembley, London. It sells single-origin coffees in 200g
bags, easy-drip single-serve pouches, brew bags and subscriptions, plus an
"EASYDRIP Coffee Collection Mix&Match" box, in GBP — 21 coffee products in the
catalogue.

## Address

- Unit 3, 284 Water Road, Wembley, HA0 1HX — United Kingdom.

## Schedules & Shipping

- Orders placed before midnight (Mon–Thu) are packed and dispatched the next
  day; orders placed after midnight are dispatched the next working day.
- UK delivery is next working day; DHL Next Working Day Delivery is £6.00.
- London deliveries aim for next day via Packfleet (per the shipping policy).

## Philosophy & Quirks

- A family of coffee professionals behind the brand — including the World
  Cezve/Ibrik Champion of 2018 and the Ukrainian Barista Champion of 2010
  (per their about page).
- Started with carefully selected coffees in drip bags — an easy-drip
  convenience format for "coffee that fits your pace".
- Single-origin focus; the "EASYDRIP Coffee Collection Mix&Match" is a mixed
  single-serve coffee box (flagged as a tasting kit).

## Scraping Quirks

- Wix storefront, not Shopify — `products.json` returns 400.
- Wix category pages render their product tiles client-side (only one card is
  server-rendered), so products are discovered from the
  `store-products-sitemap.xml` (24 entries) instead of category crawling.
- 3 `*-subscription` products are excluded → 21 coffees.
- Product pages (`/product-page/<slug>`) are narrowed to `<main>` (~98% token
  reduction); the `product:availability` meta (`InStock`/`OutOfStock`) is
  re-injected into the narrowed soup for stock state.
- Currency is pinned to GBP.
- The Mix&Match box is flagged `is_tasting_kit` / `requires_review`.

## Sources

- https://www.bearwithmecoffee.co.uk
- https://www.bearwithmecoffee.co.uk/store-products-sitemap.xml
- https://www.bearwithmecoffee.co.uk/category/coffee-beans
