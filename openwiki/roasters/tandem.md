---
type: "Reference"
title: "Tandem — Roaster Profile"
description: "Portland, Maine roaster founded in 2012 by Will and Kathleen Pratt, combining a cafe-roastery, bakery and rotating origin-focused coffee programme."
---

# Tandem — Roaster Profile

## Overview

Tandem Coffee Roasters was founded in Portland, Maine, in **2012** by Will and
Kathleen Pratt. Its Shopify shop carries rotating single origins, seasonal
blends, instant coffee, subscriptions and a producer-focused Tandem x Kamavindi
Coffee Lab collaboration. Tandem also operates a second coffee-and-bakery
location in Portland's West End.

## Address

- 122 Anderson St, Portland, ME 04101, United States — the cafe-roastery.

## Sourcing & Transparency

- Tandem says it sources at origin and works in partnership with small growers
  and specialty importers. Its current Kamavindi collaboration is with Peter
  Mbature, his family and Kamavindi Coffee Lab, connecting Tandem with Kenyan
  producers. No per-kg price transparency is stated on the pages checked.

## Schedules & Shipping

- Coffees are roasted to order on **Mondays, Wednesdays and Thursdays** and ship
  the following day. Domestic delivery is expected within **3-5 business days of
  roasting**.
- Standard shipping is free over **$50 USD** within the contiguous United
  States. Shipping to other US states and territories is calculated at checkout;
  international shipping is not currently offered.

## Philosophy & Quirks

- Tandem's public-facing motto is **“Spread Joy”**, and its “The Good Thing”
  subscription combines coffee with vinyl records.

## Scraping Quirks

- Registry key: `tandem`. The Shopify `coffees` collection mixes beans with
  instant coffee and subscriptions, so the scraper excludes those slugs and
  canonicalises collection URLs to `/products/<handle>`. Bean detail metadata is
  kept from `div.prodmeta`; sampler products are not excluded by the scraper's
  current generic slug list.

## Sources

- https://www.tandemcoffee.com/pages/our-story
- https://www.tandemcoffee.com/policies/shipping-policy
- https://www.tandemcoffee.com/pages/tandem-x-kamavindi-coffee-lab
- https://www.tandemcoffee.com
