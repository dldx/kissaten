---
type: "Reference"
title: "Cedar Coffee Roasters — Roaster Profile"
description: "Cape Town (Woodstock) specialty roaster on a Shopify storefront priced in ZAR — founded by a South African Barista Champion and a Rosetta Roastery veteran, with an Untitled Roast playlist series."
---

# Cedar Coffee Roasters — Roaster Profile

## Overview

Cedar Coffee Roasters is a specialty coffee roastery in Woodstock, Cape Town,
South Africa, selling on a Shopify storefront priced in ZAR. It was founded by
Leigh Wentzel and Winston Thomas, who each spent over seven years at leading
South African roasteries before starting Cedar; the line-up is seasonal single
origins (Ethiopia, Kenya, Colombia, Costa Rica, Rwanda), house blends
(Cedar Blend, Milky Way), a decaf and filter-drip sachets.

## Address

- Side Street Studios, Woodstock, Cape Town, South Africa (their store, per
  the shipping guide; full street address not published on site).

## Schedules & Shipping

- Free shipping on orders over R650 (site-wide banner).
- Local delivery (Cape Town CBD area and Southern Suburbs zones): R59 per
  order, delivered every Wednesday for orders placed before Tuesday 16:00.
- National delivery (South Africa): free on orders of R649 or more to major
  centres, otherwise a R60 courier fee; delivery within 2–3 working days.
- Free collection at the Side Street Studios store, Monday to Friday 09:00–16:00.

## Philosophy & Quirks

- Stated aim: "Coffee should be seen as a necessity instead of this niche
  product" — bridging the gap from commodity to specialty coffee consumers
  through sustainable sourcing and education.
- Founders' résumés are part of the brand: Winston Thomas won the South
  African Barista Championships in 2017, 2018 and 2020 and the African Barista
  Championships in 2019, and is a licensed SCA Trainer (AST); Leigh Wentzel
  rose from driver to roastery manager at Rosetta Roastery and was part of the
  team that won Coffee Magazine Roastery of the Year in 2018 and 2019.
- The store also runs an "Untitled Roast" series tied to a music-playlist
  concept (e.g. Untitled Roast Vol. 81) plus SCA courses and public cuppings.

## Scraping Quirks

- The site curates a dedicated `coffee` collection (beans, blends, decaf,
  pods); `collections/all` additionally mixes brewers, grinders, SCA courses,
  merch and gift cards, so the scraper uses the curated collection and drops
  the compostable coffee pods via `exclude_slugs`.
- Product URLs are canonicalised to the no-collection `/products/<handle>`
  form the live site serves.
- The store runs Shopify Markets with currency geolocation, so the scraper
  pins `store_currency` to ZAR and removes the `Accept-Language` header so a
  datacenter IP is never stamped with converted prices.

## Sources

- https://cedarcoffeeroasters.com
- https://cedarcoffeeroasters.com/pages/about-us
- https://cedarcoffeeroasters.com/pages/shipping-guide
- https://cedarcoffeeroasters.com/pages/contact
