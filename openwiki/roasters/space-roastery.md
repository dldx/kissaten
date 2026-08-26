---
type: "Reference"
title: "Space Coffee Roastery — Roaster Profile"
description: "Yogyakarta roastery founded by home brewers, making Indonesian specialty coffee available online from its Space Roastery shop and slow bar."
---

# Space Coffee Roastery — Roaster Profile

## Overview

Space Coffee Roastery is based in Yogyakarta, Java, Indonesia. In its story,
the founders describe learning to brew at home abroad, returning to Indonesia
and starting to roast after finding quality coffee difficult to obtain
consistently. The site sells blends, single origins, limited releases and
commodity coffee, alongside tools and a slow bar.

## Address

- Gang Loncang 88, Jalan Magelang, Yogyakarta, Indonesia — the site publishes
  this address for its office/slow bar and shop; it does not separately label
  the roasting room.

## Philosophy & Quirks

- “Space” is explained both as room for home brewing and as a reference to
  coffee that is “out of this world.” The founders say the goal is to build
  Indonesian home brewers and habitual drinkers.

## Scraping Quirks

- The scraper visits separate Blend, Single Origin and Limited Release product
  sections and uses Playwright for the JavaScript storefront.
- It adds `-capsule` and `any-coffee-you-like` to the base URL exclusion rules;
  these are genuine catalogue filters, not general platform assumptions.

## Sources

- https://spaceroastery.com
- https://spaceroastery.com/about
- https://spaceroastery.com/contact
