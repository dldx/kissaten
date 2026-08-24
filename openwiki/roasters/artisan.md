---
type: "Reference"
title: "Artisan Coffee — Roaster Profile"
description: "London coffee business and Artisan Coffee School that sources its beans exclusively from Curious Roo Coffee Roasters — founded by Edwin and Magda, who started on a Diedrich IR-12 in a warehouse."
---

# Artisan Coffee — Roaster Profile

## Overview

Artisan Coffee (artisancoffee.co.uk, London) operates a café plus the
**Artisan Coffee School**. Rather than roasting itself, it explicitly sources its
beans from **Curious Roo Coffee Roasters** (curiousroo.com, London W4 5PY) — the
site's "Online Store" links through to curiousroo.com/products/. Artisan describes
Curious Roo as "an independent small batch roastery... they take a lot of love,
great ingredients, expertise in roasting."

The scraping target for this registry is therefore the **Curious Roo Shopify
store**, which carries the shared bean range.

## Address

- 11 Power Road, London W4 5PY — United Kingdom (the Curious Roo roastery; the
  shop for the Artisan Coffee brand)

## Roasting & Equipment

- Curious Roo was founded by **Edwin and Magda**, both of whom spent a year in
  Uganda before founding the business.
- They started with a **small Diedrich IR-12** in a beat-up warehouse at
  Number 2 British Grove; in 2024 they transformed a **disused former scuba
  diving centre** into their roasting facility.

## Philosophy & Quirks

- The team includes **Kasia (Head of Coffee)** and **Peter (Head of Training,
  Artisan Coffee School)** — tying the roastery and the coffee school together.
- Range: the Barn Door Blend, single origins (e.g. Brazil-Agata, Colombia-El
  Indio, Colombia-Sweet Valley, Peru-Mikan, Kenya-Tegu, Ethiopia Beshasha/Sadi),
  and a Decaf.

## Scraping Quirks

- **Domain correction**: the "Artisan Coffee" brand sources its beans from
  **Curious Roo** — the Artisan site's "Online Store" points at curiousroo.com,
  and `artisancoffee.co.uk` is a dead domain. The scraper therefore targets the
  Curious Roo Shopify store (`ShopifyJsonScraper` on curiousroo.com), not an
  Artisan-hosted shop.

## Sources

- https://curiousroo.com/pages/about
- https://www.artisancoffee.co.uk/about/
- https://curiousroo.com