---
type: "Reference"
title: "Archers Coffee — Roaster Profile"
description: "Dubai specialty roaster with pour-over, espresso/milk and bespoke-blend collections on Shopify."
---

# Archers Coffee — Roaster Profile

## Overview

Archers Coffee is a Dubai-based specialty coffee roaster in the United Arab
Emirates. Its Shopify shop separates coffees into espresso/milk, pour-over and
bespoke-blend collections. The registered range is described as single-origin
coffees, espresso blends and bespoke blends; a verifiable production address,
roast cadence and shipping schedule were not published on the accessible pages.

## Address

- Dubai — United Arab Emirates; full roastery address not published on the accessible site pages.

## Scraping Quirks

- Three Shopify JSON collections are merged: `espresso-milk-coffees-2025`,
  `pour-over-coffees-2025` and `bespoke-blends-2025`.
- Collection-prefixed product URLs are canonicalised to `/products/<handle>`.
  This is important because one physical product can appear in multiple
  collections; the change prevents duplicate re-scrapes and false out-of-stock
  history. Non-coffee handles include subscriptions, gifts, wholesale,
  equipment, merchandise, academy and bundles.

## Sources

- https://archerscoffee.com
- https://archerscoffee.com/collections/espresso-milk-coffees-2025
- https://archerscoffee.com/collections/pour-over-coffees-2025
- https://archerscoffee.com/collections/bespoke-blends-2025
