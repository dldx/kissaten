---
type: "Reference"
title: "Monsoon Estates — Roaster Profile"
description: "Warwickshire (Stratford-upon-Avon) whole-bean roaster on Shopify selling single origins and blends in GBP alongside barista training courses and gift subscriptions."
---

# Monsoon Estates — Roaster Profile

## Overview

Monsoon Estates Coffee Company (monsoonestates.co.uk) is a UK whole-bean
coffee roaster based in Stratford-upon-Avon, Warwickshire (the site titles
itself "Monsoon Estates Coffee Roasters Stratford upon Avon Warwickshire").
The Shopify storefront sells in GBP: single-origin coffees and blends —
including monsooned Indian coffees such as Monsoon Malabar and The Bloke
Monsoon Malabar — alongside training courses (Barista Course, Latte Art,
Home Barista, Coffee Experience), gift cards and gift subscriptions.

## Address

- Unit 2 Alscot Park, Stratford upon Avon, Warwickshire, CV37 8BL — United
  Kingdom (per their contact page).

## Schedules & Shipping

- No roasting cadence or dispatch schedule published; no free-delivery
  threshold published on the pages checked.

## Scraping Quirks

- Shopify products.json; whole-bean coffees are the Coffee-typed products
  while training courses, gift cards and subscriptions are non-coffee types
  filtered out by the scraper.
- The store consistently misspells "Swiss Water Decaf" (as "Swiss Water") in
  product titles/handles; this is scraped faithfully as-is and is not a data
  error to correct.
- The "Coffee Selection" sampler product is kit-flagged (`is_tasting_kit` /
  `requires_review`) and flows through the admin review queue, never
  excluded.
- A "Roaster's Choice" dark/medium pair failed Gemini extraction on the first
  run and is re-tried on subsequent sessions.

## Sources

- https://monsoonestates.co.uk
- https://monsoonestates.co.uk/pages/about
- https://monsoonestates.co.uk/pages/contact