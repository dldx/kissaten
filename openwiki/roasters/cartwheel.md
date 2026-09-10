---
type: "Reference"
title: "Cartwheel Coffee — Roaster Profile"
description: "Nottingham roastery-café-bakery hybrid on a Probat Probatone 12 — farm-named traceable coffees, an electric van, chaff-to-allotment composting and one of the oldest roasteries in Nottingham."
---

# Cartwheel Coffee — Roaster Profile

## Overview

Cartwheel Coffee is an independent roastery and café group in Nottingham,
England, running a Shopify storefront at
[cartwheelcoffee.com](https://cartwheelcoffee.com). The roastery has sat in
Roden House in Sneinton since 2018 — a hub of independent businesses that
also houses their bakery — with cafés in Nottingham city centre and Beeston
(the latter rebranded from "The Bean", the coffee shop where founder Alex
grew up working for his mum). Per their site they are "one of the oldest
coffee roasteries in Nottingham". Most coffees are named after the farms or
cooperatives they come from.

## Address

- Roden House, Sneinton, Nottingham — England, United Kingdom (roastery and
  production HQ since 2018; full street address not published on site).
  The two cafés and the bakery are separate locations, described in the
  Overview.

## Sustainability

- Coffee bags 100% recyclable; tasting cards made from recycled coffee cups.
- Waste chaff and grounds from the roastery go to allotments for compost.
- Energy from 100% renewable sources — including fuel for their electric van.

## Sourcing & Transparency

- Buys traceable, higher-quality coffee from individual farmers and washing
  stations, "influenced by flavour more than price".
- Coffees are named after the individual farms or cooperatives where they
  were grown, and the roastery pays fairly and supports small farmers with
  expert advice to improve crop quality (no price figures published).

## Roasting & Equipment

- Probat **Probatone 12** drum roaster at the Roden House HQ, which also
  hosts home-brewing / home-espresso workshops and wholesale training.

## Schedules & Shipping

- Orders dispatched within 24 hours (excluding weekends), subject to stock
  and roasting schedule.
- Standard UK shipping: Royal Mail 48 (2–3 working days); Royal Mail 24 and
  DHL next-day available at extra cost.
- **Free UK delivery over £30**; below that a £2.60 flat fee applies.
- International: orders under 2kg via Royal Mail Tracked International
  (3–5 working days Europe, 6–7 worldwide); over 2kg via DHL at checkout
  rates.
- Coffee is vacuum-sealed and nitrogen-flushed; they aim to send coffee
  within three weeks of roast, and consider it at its best from around three
  weeks onwards.

## Philosophy & Quirks

- Multiple accredited Q-Graders on the team (including founder Alex, who
  qualified after years working his way through every role in his mum's
  Beeston café from age eight).
- Their own "humble brag": Q-Graders, one of the oldest roasteries in
  Nottingham, and "a 5-star review from our founder's Mum on Google".
- Education is part of the offer: coffee tastings for subscription
  customers, 1-1 home-brewing workshops and online barista qualification
  courses.

## Scraping Quirks

- The scraper reads the curated `/collections/coffee/products.json` (not the
  root catalogue) and applies a broad substring exclusion list for
  non-coffee products (subscriptions, equipment, gifts, merch, tea, etc.).
- That exclusion list also catches the **Taster's Pack Gift Set** — a coffee
  sampler kit and hero product on the homepage — because its handle
  contains `gift`; the kit never enters the catalogue rather than flowing
  through the tasting-kit review queue.
- Product URLs are normalised by stripping the collection segment so they
  point at the canonical `/products/<handle>` form.

## Sources

- https://cartwheelcoffee.com/
- https://cartwheelcoffee.com/pages/about
- https://cartwheelcoffee.com/pages/roastery
- https://cartwheelcoffee.com/pages/faq
- https://cartwheelcoffee.com/pages/delivery-and-shipping
- https://cartwheelcoffee.com/blogs/articles/cartwheel-coffee-origins