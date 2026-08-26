---
type: "Reference"
title: "People's Possession — Roaster Profile"
description: "European specialty coffee brand with a deliberately irreverent manifesto built around radical sourcing and superior roasting."
---

# People's Possession — Roaster Profile

## Overview

People's Possession is a European specialty coffee brand registered in Kissaten
as based in France. Its online shop sells coffee and merchandise, and its
manifesto presents the brand as a playful “survival guide” for finding
well-sourced, well-roasted beans. The storefront is a WordPress shop.

## Address

- France — full roastery address not published on the consulted site pages.

## Sourcing & Transparency

- The manifesto explicitly describes the brand's promise as “radical sourcing”
  and “superior roasting”, but the consulted pages publish no producer-paid
  prices, volumes or cost breakdown.

## Philosophy & Quirks

- The brand's “Bring Your Own Beans” manifesto treats its cans as protected
  property and warns readers against free coffee and questionable beans. It is a
  genuine brand voice rather than a conventional sourcing or brewing guide.

## Scraping Quirks

- Product pages may disappear when sold out, so the scraper forces extracted
  beans to `in_stock=True`. It uses Playwright for the shop listing, accepts
  `/product/` links and excludes `/lid`, `/posters`, `/coin`, sleeves and tattoos.

## Sources

- https://peoplepossession.com/manifesto/
- https://peoplepossession.com/shop/
