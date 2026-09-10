---
type: "Reference"
title: "Elsewhere Coffee — Roaster Profile"
description: "Deptford, South East London roastery (est. 2019) with escape-themed coffees (Daydreamer, Sugar Glider, Whirlpool), electric-van eco-bucket wholesale delivery and four cafés across London."
---

# Elsewhere Coffee — Roaster Profile

## Overview

Elsewhere Coffee is a South East London roastery that has been hand roasting
specialty coffee from its neighbourhood HQ in Deptford **since 2019**, built
on the idea that "great coffee can transport you". The range carries the
theme through: Daydreamer, Juicebox, Night Rider, Melon Drop, Sugar Glider,
Whirlpool, Fuzzy Peach — plus a **Special Release** collection and an
"Uncommon" line of 100g Gesha jars. Alongside the roastery it runs four café
sites across London (Brew Bar at the HQ, two Daydreamer cafés and a Hackney
Central kiosk). The storefront is Shopify at
[elsewherecoffee.com](https://elsewherecoffee.com).

## Address

- Elsewhere Coffee LTD, Unit 3 / 3 Titan Business Estate, Railway Arches
  (Ffinch Street), London SE8 5QA, United Kingdom — the Deptford roastery,
  also home to the Brew Bar café

## Sustainability

- London wholesale coffee is delivered in **refillable eco-buckets by their
  own electric van**; further-afield orders ship in fully recycled bags via a
  **carbon-offset 24-hour courier** (per their site).

## Sourcing & Transparency

- Publishes producer/farm partner profiles on its site: Jairo Arcila (Santa
  Mónica, Colombia), Finca Churupampa (Cajamarca, Peru), Lot 20 Coffee
  (Kericho, Kenya), Mió (Minas Gerais, Brazil) and more.
- Works through trusted importers with an emphasis on long-term
  relationships and fair prices; no price-transparency figures are published.

## Schedules & Shipping

- Subscription coffee is **roasted to order** with **free shipping on every
  subscription order** (weekly, bi-weekly or monthly cadence; 10% off beans).
- Wholesale: no MOQs, and **free delivery on orders over 10kg**; delivered
  by electric van in London, or 24-hour courier elsewhere. Delivers
  worldwide.
- No per-region consumer shipping rates are published on the site.

## Philosophy & Quirks

- Brand built on curiosity and escape: "coffee that invites you to slow
  down, explore new origins, and discover moments of escape in each cup";
  the tagline is literally "Take me Elsewhere".
- Ethos of being "inviting, not intimidating; thoughtful without pretension".
- The HQ Brew Bar doubles as the **Brew Lab**, a space for high-end prosumer
  gear, and hosts brewing courses and events.
- Runs periodic prize draws for customers (a Fellow Series One espresso
  machine and a trip to Brazil at the time of writing).

## Scraping Quirks

- The scraper reads only the **frontpage collection's** `products.json`
  rather than `/collections/all`, so products not surfaced on the front
  collection may be missed.
- Product URLs are normalized by `preprocess_product_url`, which strips
  collection segments (`/collections/<x>/products/<handle>` →
  `/products/<handle>`) before product-page processing.

## Sources

- https://elsewherecoffee.com/
- https://elsewherecoffee.com/pages/about-us
- https://elsewherecoffee.com/pages/cafe
- https://elsewherecoffee.com/pages/subscription-new
- https://elsewherecoffee.com/pages/wholesale-new
- https://elsewherecoffee.com/policies/contact-information
