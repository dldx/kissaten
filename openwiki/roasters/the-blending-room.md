---
type: "Reference"
title: "The Blending Room — Roaster Profile"
description: "Independent Hull (East Yorkshire) coffee roaster, roasting since 2009, with a full-service offer and a curated whole-bean catalogue on a Shopify storefront."
---

# The Blending Room — Roaster Profile

## Overview

The Blending Room (www.theblendingroom.co.uk) is an independent coffee
roasting company in Hull, East Yorkshire, roasting since 2009. Started on
Beverley market, it now roasts for outlets across Hull, East Yorkshire,
Yorkshire and North Lincolnshire and offers a full-service experience —
training, equipment supply (partnering with Sanremo, Victoria Arduino, La
Marzocco, Mahlkönig and Marco) and maintenance (per its Our Story page). The
Shopify storefront sells whole-bean coffee in GBP.

## Address

- The Blending Room Ltd, 30 Unit Factory Estate, Boulevard, Hull, HU3 4AY,
  United Kingdom (published in the site footer and contact page).

## Scraping Quirks

- Shopify JSON-only from the curated `/collections/coffee`; a strict Shopify
  `product_type == "Coffee"` include-filter reproduces the whole-bean set
  without hardcoded names.
- Two curated variety-pack samplers carry no standard kit token in their
  handles, so a custom postprocessor forces `is_tasting_kit` on
  `variety-pack` URLs — the Core Coffee Variety Pack is kept and flagged into
  the review queue (the single-origin variety pack was dropped at e2e).
- Canonical product pages are the no-collection form; the collection segment
  from the products.json base is stripped.
- e2e: 10 coffee products saved + 1 kit flag.

## Sources

- https://www.theblendingroom.co.uk
- https://www.theblendingroom.co.uk/pages/contact-us
- https://www.theblendingroom.co.uk/collections/coffee