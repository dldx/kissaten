---
type: "Reference"
title: "Small Batch Roasting Co. — Roaster Profile"
description: "North Melbourne roastery (since 2009) buying at the farm gate via sister company Shared Source — #powertotheproducer transparency, parchment-form purchases and interest-free producer loans."
---

# Small Batch Roasting Co. — Roaster Profile

## Overview

Small Batch Roasting Co. is a North Melbourne, Australia roastery that has been
"roasting exceptional coffee since 2009, celebrating socially positive and
agriculturally sustainable sourcing". Founder Andrew Kelly started with backyard
roasting experiments ("a heat gun and colander") before opening flagship café
Auction Rooms in North Melbourne in 2008 — twice named Melbourne's best café by
The Age Good Cafe Guide — and then a dedicated roastery down the road. The
storefront is **WooCommerce/WordPress** (smallbatch.com.au), with a separate
Square-based "Cellar Door" site for pastry and grocery pre-orders.

## Address

- 3-9 Little Howard St, North Melbourne, Victoria 3051, Australia

## Sourcing & Transparency

- Unusually deep public transparency, under the hashtag **#powertotheproducer**:
  a dedicated blog post ("Green Coffee Sourcing and Transparency") spells out
  how they buy and what they pay.
- Green coffee is bought via sister company **Shared Source S.A.S.** (since
  2016), which exports directly from Colombia and imports from there and other
  origins.
- Four guiding principles: prices that reflect growers' need to make a good
  livelihood; year-round producer contact; **interest-free cash loans** for
  farm infrastructure and living costs; and educating/empowering producers to
  transition to organic and sustainable agriculture.
- They buy **in parchment form, at the farm gate, in the producer's local
  currency**, assuming risk and cost from that point; they pay a premium for
  transition to chemical-free/holistic practices and a post-hoc bonus when a
  coffee performs well on the menu — including on coffees that go into blends,
  not just single origins.
- Preference for smallholders "least able to otherwise gain access to an
  international buyer"; working origins include Colombia, Guatemala, Kenya and
  Ethiopia, with a peer-to-peer regenerative-farming training programme in
  Colombia.

## Philosophy & Quirks

- Signature filter blend **Golden Ticket** (launched 2017) is named after the
  Willy Wonka song — a blend of several single-origin coffees described as a
  "daily driver".
- Seasonal espresso is called **The Ones We Love**; a December limited series
  runs as "12 Roasts of Christmas".
- Wholesale is deliberately selective: "Small Batch isn't for every cafe."
- Auction Rooms was twice named Melbourne's best cafe by The Age Good Cafe
  Guide (per their site).

## Scraping Quirks

- **Name collision**: this is the Melbourne roaster — not "Small Batch Coffee
  Roasters" of Brighton & Hove, UK, which is a different company (UK profile
  lives under `small_batch_coffee_roasters`).
- The scraper crawls only the coffee-only categories (espresso/filter/
  bundles); the decision to include a product is made on the **card's display
  name**, not the URL — the global URL-level "ticket" exclusion would
  otherwise wrongly drop the **Golden Ticket** coffee.
- Bundle products (`bundle`, `4_bundle` in the URL) are flagged
  `is_tasting_kit` / `requires_review` and flow through the review queue
  rather than being excluded.
- Sold-out variable products are filtered by "out of stock"/"sold out" text on
  the product card; WooCommerce permalinks must match
  `/shop/<category>/<slug>/`.

## Sources

- https://www.smallbatch.com.au/about-us/
- https://www.smallbatch.com.au/contact-us/
- https://www.smallbatch.com.au/something-to-shout-about/
- https://www.smallbatch.com.au/farm-to-roastery/
- https://www.smallbatch.com.au/about-us/wholesale/
- https://www.smallbatch.com.au/shop/