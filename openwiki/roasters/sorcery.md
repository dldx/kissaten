---
type: "Reference"
title: "Sorcery Coffee Roasters — Roaster Profile"
description: "Pretoria light-roast specialty roaster on a Shopify storefront priced in ZAR — two walk-in-only cafés (Hillcrest and Wapadrand) with different origins always in the hopper."
---

# Sorcery Coffee Roasters — Roaster Profile

## Overview

Sorcery Coffee Roasters is a specialty coffee roastery in Pretoria, South
Africa, selling light-roasted coffee on a Shopify storefront priced in ZAR.
The bean range is split across two storefront ranges — "Approachable" and
"Progressive" — currently dominated by Colombian single origins plus
Guatemala and Nicaragua lots, with different origins always in the hopper at
the cafés. The company operates two full-service café/roastery venues in
Pretoria: Sorcery Hillcrest (177 Lunnon Rd) and Sorcery Ruins (3 Diep in die
Berg, Wapadrand).

## Address

- Full roastery address not published on site; the venues listed are 177
  Lunnon Rd, Hillcrest, Pretoria and 3 Diep in die Berg, Wapadrand, Pretoria,
  South Africa (the FAQ describes the company as "first and foremost a coffee
  roastery / cafe").

## Schedules & Shipping

- Free shipping on orders over R800 (site-wide banner).
- Venue hours: Hillcrest Mon–Fri 07:00–16:00, Sat–Sun 08:00–16:00; Ruins
  Mon–Fri 08:00–17:00, Sat–Sun 09:00–17:00 (winter closes 16:30); public
  holidays 09:00–16:00/17:00.

## Philosophy & Quirks

- "At Sorcery we pride ourselves on light roasted specialty coffee", with a
  wide range of profiles "from traditional chocolate and nutty flavours to
  light, fruity and floral notes".
- The cafés have a strict no-reservations, walk-ins-only policy — the FAQ
  pointedly declines functions, bookings and even weddings disguised as
  photoshoots; photoshoots cost R700 for the first hour (R400 for the second,
  capped at two hours).
- General enquiries via info@sorcerycoffee.co.za; photoshoot bookings via
  hello@sorcerycoffee.co.za.

## Scraping Quirks

- No dedicated "coffee" collection exists: the bean range is the union of the
  `approachable` and `progressive` collections, which equals
  `collections/all` (8 products on capture: 7 coffees plus compostable coffee
  pods). The scraper uses `collections/all` and drops the pods via
  `exclude_slugs`.
- Product URLs are canonicalised to the no-collection `/products/<handle>`
  form the live site serves.
- The store runs Shopify Markets with currency geolocation, so the scraper
  pins `store_currency` to ZAR and removes the `Accept-Language` header so a
  datacenter IP is never stamped with converted prices.

## Sources

- https://sorcerycoffee.co.za
- https://sorcerycoffee.co.za/pages/cafes
- https://sorcerycoffee.co.za/pages/faq
