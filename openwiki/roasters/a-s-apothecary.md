---
type: "Reference"
title: "A S Apothecary — Roaster Profile"
description: "Isle of Harris apothecary that also roasts small-batch specialty coffee, buys mostly from women's co-operatives, wastes nothing, and blends espresso using 'perfume theory'."
---

# A S Apothecary — Roaster Profile

## Overview

A S Apothecary is an organic skincare / apothecary brand based on the Isle of Harris
(Outer Hebrides, Scotland) that also roasts a small range of specialty coffee.
Founder Amanda Saurin frames the whole enterprise as: "At the root of A.S Apothecary
is the desire to live harmoniously." The coffee arm operates a
[Shopify storefront at asapoth.com](https://asapoth.com) that is a **mixed store** —
roughly 87 products of which only ~7 are coffee; the rest are skincare, soap, tea
and merch.

## Address

- Isle of Harris, Outer Hebrides, Scotland — United Kingdom (a croft/smallholding;
  full street address not published on the site)

## Sustainability

- Per their site, they buy coffee **mostly from women's co-operatives across the
  coffee belt** and roast small-batch specialty beans on Harris.
- The coffee page is explicit about closing loops: "Coffee is a fresh fruit. We
  roast the beans, the chaff makes great bedding for our hens, the leftover coffee is
  ground and used in our soap or as a slug deterrent in the greenhouse. Nothing is
  wasted."

## Roasting & Equipment

- Small-batch roasting on the island of Harris itself (no commercial-scale
  roastery — beans are roasted in-house at the shop scale).

## Philosophy & Quirks

- Their **Seasonal Espresso** is blended using "perfume theory": citrus top notes, a
  floral/fruity heart, and a chocolatey/nutty base — a flavour architecture
  borrowed from perfumery.
- Unusual transparency for a mixed apothecary/coffee store: the single-origin line
  publishes **cupping scores** (e.g. Ethiopia Taferi Kela at 86.75) and exotic
  processes like an anaerobic "Kickstart" lot.

## Scraping Quirks

- **Mixed store**: the Shopify storefront carries ~87 products but only ~7 are
  coffee — skincare, soap and herbalism are the core business, coffee is a side
  product. The scraper uses an **include-only filter** — a product is kept only
  if its `product_type` is coffee or its title matches the `"<Country> - <name>"`
  single-origin pattern (with a fallback allow-list of verified coffee handles).

## Sources

- https://asapoth.com/pages/about-us
- https://asapoth.com/pages/about-our-coffee
- https://asapoth.com/pages/mission-statement