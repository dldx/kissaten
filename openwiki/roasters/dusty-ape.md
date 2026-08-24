---
type: "Reference"
title: "Dusty Ape — Roaster Profile"
description: "Wiltshire coffee roastery & coffee bar (Bath Beverages Ltd) on Shopify at dustyape.com — single origins, estates/microlots, blends, decaf and a Cafetière Tasting Pack."
---

# Dusty Ape — Roaster Profile

## Overview

Dusty Ape Coffee Roastery & Coffee Bar (Bath Beverages Ltd) is based in Hilperton, Wiltshire, on a Shopify storefront at dustyape.com. Its catalogue covers single origins, estates/microlots, blends (Molten Toffee, Silverback, Capuchin, Snow Monkey) and decaf, sold in 227g/1kg with grind options, plus a Cafetière Tasting Pack.

## Address

- Unit 1 Marsh Farm Industrial Estate, Hilperton, Wiltshire BA14 7PJ — United Kingdom

## Philosophy & Quirks

- Founded in 2013 by Phil Buckley & Evan Metz; roasts on a 15kg roaster.
- Operates under the Bath Beverages Ltd parent company, running a roastery and coffee bar.
- An aficionado taster-pack line (the Cafetière Tasting Pack) flows through the review queue.

## Scraping Quirks

- The listed domain dustyape.co.uk is a GoDaddy parking lander (never hosted the shop) — the real store is dustyape.com.
- Use the ROOT products.json: the `our-coffees` collection advertises 112 products but only publishes 21, and the Cafetière Tasting Pack exists only on the root payload.
- The tasting-pack handle is `cafetiere-tasting-pack`, flagged `is_tasting_kit`/`requires_review` — the base `taster-pack`/`sample-pack` patterns wouldn't match it, so a `tasting-pack` pattern was added.
- Collection page counts are unreliable.

## Sources

- https://dustyape.com
- https://dustyape.com/products.json