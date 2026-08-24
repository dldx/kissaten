---
type: "Reference"
title: "Cairngorm Coffee — Roaster Profile"
description: "Edinburgh specialty coffee roaster (Shopify) roasting filter and espresso coffees, especially Ethiopian/Burundi single origins, plus a cupping sample box set, decaf, cascara tea and subscriptions."
---

# Cairngorm Coffee — Roaster Profile

## Overview

Cairngorm Coffee is an Edinburgh specialty coffee roaster operating a Shopify
storefront at cairngorm.coffee. It roasts filter and espresso coffees,
especially Ethiopian, Burundi and single origins, and also sells a cupping
sample box set, decaf, cascara tea and subscriptions.

## Address

- Edinburgh, Scotland — United Kingdom (street address not published; based in
  Edinburgh).

## Philosophy & Quirks

- Releases include single-farmer/community lots (e.g. Migoti Hill from the
  Mutambu Commune, Burundi; Santa Luz; Summer Banger; a Eucalyptus
  co-fermentation).

## Scraping Quirks

- cairngormcoffee.com redirects to cairngorm.coffee.
- The `coffee` collection contains a `cupping-box-set` (sample/cupping box)
  which is a tasting kit and **must** flow through the review queue — the base
  `cupping` exclusion pattern is overridden so it is flagged
  `is_tasting_kit`/`requires_review`, not dropped.
- Cascara (coffee-cherry tea) is excluded as a non-bean beverage; subscriptions
  are excluded.
- Product detail (producer/origin/process/variety/altitude) lives on the
  rendered page, not in products.json, so the scraper page-scrapes with soup
  pruning.

## Sources

- https://cairngorm.coffee
- https://cairngorm.coffee/collections/coffee