---
type: "Reference"
title: "Wanderlust Espresso — Roaster Profile"
description: "Richmond Upon Thames mobile coffee-catering business that roasts small weekly batches for its Wix shop — Cosmic and Aeronaut blends plus Latin American singles, roasted on Tuesdays."
---

# Wanderlust Espresso — Roaster Profile

## Overview

Wanderlust Espresso Ltd is a mobile coffee-catering business in Richmond Upon
Thames, London — espresso bars, pour-over bars and smoothie bars for
exhibitions, conferences, brand activations, offices, luxury events and film
shoots — that also sells roasted coffee beans online through a Wix storefront
at [wanderlust-espresso.com](https://www.wanderlust-espresso.com). The bean
side is a small sideline: a handful of blends (Cosmic, Aeronaut Espresso,
Beleza) and single origins from Latin America (Brazil, Peru, Colombia/Guatemala
decaf) at £8.00–£9.40, alongside Coffee Brewing Kit (Kinto servers, Hario
papers) and coffee-themed art prints. The business began in autumn 2018 as a
family venture run by Kostas — over two decades in coffee, after "more than a
decade working with one of the biggest coffee companies in the world" (per
their site) — together with Karla, his Brazilian partner.

## Address

- Suite 122, 30 Red Lion Street, Richmond Upon Thames, TW9 1RB — United
  Kingdom (the published business/contact address; no dedicated roastery
  address is published on the site, and returns go to a separate Richmond
  address, 49 Temple Road, TW9 2EB).

## Schedules & Shipping

- Roasting cadence: "roasted in limited quantities once a week on Tuesday";
  orders placed before 6pm Monday are roasted and despatched on Wednesday —
  later orders are held to the following week.
- UK shipping is weight-priced: under 2 kg £3.05 (Royal Mail 2nd Class),
  2.01–5 kg £5.99, 5.01–10 kg £6.99, over 10.01 kg £9.20 (Hermes); the UK
  zone includes Highlands & Islands.
- Free shipping is offered in the UK on orders up to 2 kg weight (no spend
  threshold published). No international shipping is offered.

## Philosophy & Quirks

- The name comes with a Tolkien epigraph: "Not all those who wander are lost".
- Coffee is framed entirely through hospitality: their stated mission is to
  make "every coffee experience at your event unique… no matter the setting,
  location or crowd size" — the online bean shop exists so event guests can
  "experience freshly roasted coffee at home".
- Product pages read like a specialty café's brew guide: each bean lists brew
  ratios (espresso 1:2 in 28–32 s; filter 60–65 g per litre) and suitable
  methods from V60 to stovetop.

## Scraping Quirks

- Beans are a sideline of a catering business: the shop mixes coffee with
  Kinto/Hario brew gear, art prints and event services. The scraper scrapes
  only `/coffee-beans`, filters sold-out `product-item-root` cards before URL
  filtering, narrows product pages to `div[data-hook=product-page]`, and pins
  currency to GBP (Wix pages carry no `og:price:currency` meta tag).
- The `/coffee-beans` listing shows a dangling "PERU — Eli Chiclon £9.00" card
  whose product page 404s, so the listing text and the reachable product URLs
  can disagree.
- Origin data on product pages is unreliable: the decaf is sold under the slug
  `decaf-brazil`, titled "Decaf - Colombia", described as Monte Bonito,
  Colombia — but its structured "Coffee Information" block lists Farm: San
  Lorenzo, Region: Caldos, Country: Guatemala. Expect extractor output to need
  scrutiny on this one.
- At the time of writing every coffee in the shop was marked Out of Stock; the
  sold-out filter means the catalogue can legitimately be empty after a run.

## Sources

- https://www.wanderlust-espresso.com/
- https://www.wanderlust-espresso.com/about-us
- https://www.wanderlust-espresso.com/contact
- https://www.wanderlust-espresso.com/coffee-beans
- https://www.wanderlust-espresso.com/product-page/cosmic-blend
- https://www.wanderlust-espresso.com/product-page/decaf-brazil
- https://www.wanderlust-espresso.com/shipping
