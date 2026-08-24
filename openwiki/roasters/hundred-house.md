---
type: "Reference"
title: "Hundred House Coffee — Roaster Profile"
description: "Ludlow (Shropshire) speciality roastery founded 2016 on Shopify at hundredhousecoffee.com — expressive single origins roasted light, blends, multi-bag bundles and a coffee-meets-art 'Art & Industry' programme (Freak & Unique releases paired with original artwork)."
---

# Hundred House Coffee — Roaster Profile

## Overview

Hundred House Coffee is an independent speciality roastery in Ludlow,
Shropshire, founded in 2016 by Matthew Wade (20+ years roasting, Q-Grader and
ex-Head Roaster at Union Hand Roasted) and Anabelle de Gersigny, building on
careers across both speciality coffee and art. The Shopify storefront at
hundredhousecoffee.com sells single origins roasted light for clarity, blends
and multi-bag bundles — the curated All Coffees collection carries ~16
products — alongside an art-meets-coffee programme.

## Address

- Unit 1, SY8 Studios, Gravel Hill, Ludlow, Shropshire SY8 1FP — United Kingdom.

## Schedules & Shipping

- Coffee is generally roasted to order, or roasted within 5 days of shipping;
  UK delivery is usually 3–5 business days (Royal Mail and FedEx).
- Free shipping on orders over £40.

## Philosophy & Quirks

- "Coffee, creativity and community" — the Art & Industry programme pairs
  coffee releases with original artwork (e.g. the Freak & Unique XX/XXI
  coffees with riso prints by Nicholas Stevenson).
- Single origins are roasted light "for clarity and complexity"; catalogue
  includes Rwandan women's cooperative coffees (Sholi Women's Coffee,
  Women's Crown).

## Scraping Quirks

- Shopify; the curated `allcoffees` collection (handle has NO hyphen) is the
  single crawl source; sibling `single-origins-*` collections are subsets.
- JSON-only: the structured spec table (Farm, Region, Altitude, Varietal,
  Process, Flavour Notes) lives in products.json `body_html`; page scraping is
  skipped and the JSON carries no roast level.
- `rwanda-special-three-bags-for-a-limited-edition-riso-print` and
  `freak-unique-bundle` multi-bag bundles are flagged `is_tasting_kit` into
  the admin review queue.
- ns-* no-sugar RTD canned drinks are excluded as non-coffee.
- Canonical product URLs are `/products/<handle>`.

## Sources

- https://hundredhousecoffee.com
- https://hundredhousecoffee.com/pages/ns-about
- https://hundredhousecoffee.com/pages/shipping-and-returns
