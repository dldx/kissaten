---
type: "Reference"
title: "La Pêche — Roaster Profile"
description: "Tiny UK specialty roaster on Shopify at lapechecoffee.co.uk with an 11-product catalogue of experimental co-ferments — Colombia Watermelon/Strawberry/Peach from Edinson Argote's Huila farms — plus washed single origins and curated collection boxes."
---

# La Pêche — Roaster Profile

## Overview

La Pêche ("La Pêche Coffee Company", with the accented ê, per their site) is a
UK specialty coffee roaster on Shopify at lapechecoffee.co.uk with a tiny,
premium 11-product catalogue — every product typed Coffee. The line-up is
dominated by experimental co-ferments from Edinson Argote's farms in Huila,
Colombia (Watermelon, Strawberry, Peach Caturra), alongside washed single
origins from Tanzania (Ngila Estate Geisha and Kent AB), Peru (Demostenes
Tantalean Geisha), Kenya (Nandi County peaberry) and a thermal-shock Laurina,
plus two curated multi-bag collection boxes. Tagline: "Celebrating the
diversity of flavour."

## Address

- United Kingdom — full street address not published on site.

## Schedules & Shipping

- Free delivery on orders over £25 (per the site banner; not valid with discount
  codes).

## Scraping Quirks

- Shopify, but no curated coffee collection exists — the root `products.json`
  (11 products) is the whole catalogue.
- JSON-only extraction: dense `body_html` already carries origin, variety,
  process and cup score, so product pages are not fetched.
- Handles carrying the `-collection-` token (Summer Co-Ferment Collection, The
  Full Collection — multi-bag tasting boxes) are flagged `is_tasting_kit` /
  `requires_review` for the admin queue.
- Canonical product URLs are `/products/<handle>`; currency pinned to GBP.

## Sources

- https://lapechecoffee.co.uk
- https://lapechecoffee.co.uk/products.json
