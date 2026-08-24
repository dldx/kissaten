---
type: "Reference"
title: "Flying Horse Coffee — Roaster Profile"
description: "UK coffee roaster on Shopify at flyinghorsecoffee.com with a small range — espresso and filter single origins, a blend and a caffeine-free roast — plus capsules and brewing gear."
---

# Flying Horse Coffee — Roaster Profile

## Overview

Flying Horse Coffee is a UK roaster on a Shopify storefront at flyinghorsecoffee.com with a small coffee range in GBP — ESPRESSO BLEND £15.95, an ESPRESSO single origin £17.95, a FILTER single origin £17.95 and a CAFFEINE FREE roast £18.95 — alongside capsules and brewing gear.

## Address

- United Kingdom (city not published on site)

## Scraping Quirks

- `/collections/coffee/products.json` is a dedicated curated collection returning exactly the 4 beans (product_type "Coffee").
- The broader `/collections/beans` mixes beans with capsules, a machine, Huskee, V60, AeroPress and Filtropa gear (excluded).
- Canonical product URLs are `/products/<handle>` (collection segment stripped).
- Caution: excluding the slug "filter" would wrongly drop the FILTER bean — the curated collection + product_type filter handle the split.
- Transient 503s are handled by the base escalation. Currency is pinned to GBP.

## Sources

- https://flyinghorsecoffee.com
- https://flyinghorsecoffee.com/collections/coffee