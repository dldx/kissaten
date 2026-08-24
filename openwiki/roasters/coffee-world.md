---
type: "Reference"
title: "Coffee World — Roaster Profile"
description: "Family-run Cambridge coffee roaster founded in 1984, roasting on IMF and Vittoria systems at its Milton roastery, with free UK delivery over £15, a sustainability programme, plus equipment, green beans and Academy courses."
---

# Coffee World — Roaster Profile

## Overview

Coffee World is an independent, family-run coffee roaster founded in
Cambridge in 1984 (40+ years of roasting), on a Shopify storefront at
coffeeworld.co.uk. Its curated catalogues cover single origins, blends and
decaf plus fixed multi-bag coffee bundles; alongside coffee it sells equipment
(it is an authorised La Marzocco dealer), grinders, green coffee,
subscriptions and Academy barista courses, and runs an Espresso Bar at the
roastery.

## Address

- 135 Cambridge Road, Milton, Cambridge CB24 6AT — United Kingdom

## Sustainability

- The Cambridgeshire roastery is powered by a large solar array.
- IMF and Vittoria roasting systems recirculate airflow (no external
  afterburner); coffee bags are from fully recycled plastic and recyclable via
  soft-plastic schemes (per their sustainability page).

## Roasting & Equipment

- Roasted at the Milton, Cambridge roastery on IMF and Vittoria systems;
  authorised La Marzocco dealer; engineers service commercial coffee machines.

## Schedules & Shipping

- Free UK delivery on orders over £15; same working-day dispatch before 1pm
  (per their site).

## Scraping Quirks

- Shopify with two curated collections — `coffee` (~38) and `coffee-bundles`
  (19 holding ~8 kept bundles) — landing ~34 beans in the catalogue; green
  coffee, subscriptions, equipment gift boxes and home-espresso packages are excluded.
- Fixed multi-bag bundles (handles carry a `<n>-x-<weight>g` token, e.g.
  `sweet-like-chocolate-3-x-250g-bundle`) are flagged `is_tasting_kit` /
  `requires_review` for the admin queue.
- `country=GB` and GBP are pinned so Shopify Markets geolocation can't convert
  the store currency.
- Canonical product URLs are `/products/<handle>`.
- The scraper's module docstring describes the business as Wolverhampton-based,
  but the live site is the 1984 Cambridge roastery — a provenance trap for
  future contributors.

## Sources

- https://coffeeworld.co.uk
- https://coffeeworld.co.uk/pages/about
- https://coffeeworld.co.uk/pages/locations
- https://coffeeworld.co.uk/pages/sustainability