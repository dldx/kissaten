---
type: "Reference"
title: "Espresso Lab Microroasters — Roaster Profile"
description: "Cape Town (Woodstock) microroaster established 2009 at The Old Biscuit Mill, on a Shopify storefront priced in ZAR — traceable small lots, a public roastery café and coffee cocktails."
---

# Espresso Lab Microroasters — Roaster Profile

## Overview

Espresso Lab Microroasters is a Cape Town microroaster established in 2009,
based at The Old Biscuit Mill in Woodstock, Cape Town, South Africa, selling
on a Shopify storefront priced in ZAR (the site's country/region selector
serves ZAR for every market). The rotating line-up is single-estate lots from
across the bean belt — Kenya, Ethiopia, Colombia, Costa Rica, Honduras, El
Salvador, Guatemala, Nicaragua, Indonesia, Peru, Rwanda — sourced from fully
traceable farms, estates and cooperatives. This is the South African
microroaster, not to be confused with the Turkish "Espresso Lab" chain
(espressolab.com) or other similarly named stores abroad.

## Address

- The Old Biscuit Mill, 375 Albert Road, Woodstock, Cape Town, South Africa.

## Schedules & Shipping

- The roastery is open to the public: Mon–Fri 08:00–16:00, Sat 08:00–15:00
  (per their about page), serving espresso and filter drinks plus "a few
  interesting coffee cocktails".
- No roasting cadence, dispatch schedule or delivery rates are published on
  the site.

## Philosophy & Quirks

- "Our daily quest is to find optimal ways in enjoying coffee, from sourcing
  small lots of freshly harvested coffee, to developing the optimal roasting
  profiles that will reflect the terroir and origin of the coffee."
- Sourcing stance per their site: coffees "from fully traceable farms, estates
  and cooperatives", seeking relationships with growers and exporters and
  "sustainable, fair and equal trade"; high-altitude lots (over 1500 m) grown
  "without the need for chemical fertilizers or pesticides".
- The product range includes a rotating house product called "HELLO, my name
  is coffee." alongside the single estates.
- Contact: info@espressolabmicroroasters.com, +27 21 447 0845.

## Scraping Quirks

- The site curates a `coffee-1` collection containing only bean products;
  the equipment sundries (grinders, aeropress, bialetti, filters, kettles,
  tumblers), books and pins live in `collections/all` and a `coffee-sundries`
  collection, which the scraper avoids (an `exclude_slugs` net guards against
  drift).
- The `drip-coffee-taste-pack` sampler in `collections/all` is NOT excluded —
  any tasting-kit products are extracted and flagged `is_tasting_kit` /
  `requires_review` into the admin review queue.
- Several products exist under duplicate `-copy` suffixed handles (e.g.
  `rwanda-shyira-nyabihu-copy` vs `rwanda-rugali-cws-nyamasheke-copy`); both
  listings are kept as separate products.
- Product URLs are canonicalised to the no-collection `/products/<handle>`
  form the live site serves; the scraper pins `store_currency` to ZAR and
  removes the `Accept-Language` header so Shopify Markets geolocation can
  never stamp converted prices.

## Sources

- https://espressolabmicroroasters.com
- https://espressolabmicroroasters.com/pages/about-us
- https://espressolabmicroroasters.com/pages/espresso-lab-microroasters
