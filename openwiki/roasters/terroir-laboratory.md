---
type: "Reference"
title: "Terroir Laboratory — Roaster Profile"
description: "Indonesian specialty roaster (TERROIR.IDN by Terroirlab) in Tangerang, Banten — experimental fermentation lots (yeast inoculation, anaerobic, extended fermentation), a Best of Panama release and IDR-only Shopify storefront."
---

# Terroir Laboratory — Roaster Profile

## Overview

Terroir Laboratory (branded **TERROIR.IDN by Terroirlab**, terroiridn.com) is an
Indonesian specialty coffee roaster based in Tangerang, Banten (greater
Jakarta). The Shopify storefront sells a small, competition-leaning catalogue —
experimental fermentation lots (yeast inoculation, anaerobic and extended
fermentation), omni-roast blends and rare lots such as Best of Panama 2025 from
Finca Los Cenizos — priced in Indonesian rupiah, plus Brew Boyy collaboration
releases and branded apparel. Roastful listed it among its *Top 100 Specialty
Coffee Roasters in 2024*.

## Address

- Ruko Hampton Avenue, Jl. Hampton Boulevard No. H/05, Mekar Jaya, Kec.
  Pagedangan, Kabupaten Tangerang, Banten 15334 — Indonesia (published in the
  site footer as the Terroir.idn / Terroirlab business address)

## Roasting & Equipment

- Positions itself as an "artisan coffee roaster" focused on fermentation
  innovation — yeast inoculation, anaerobic and extended fermentation
  processing (per their site).
- Product pages publish roast level (e.g. Omni Roast) and recommended brew
  (Espresso/Filter) in a Specifications section.

## Sourcing & Transparency

- Origin data is unusually detailed on product pages: blend components named
  at lot level (e.g. Ethiopia ALO ASD, Colombia Yeast Inoculation, Colombia El
  Mirador Ex Ferment), plus elevation/variety/process details on product cards.
- Sells competition-grade lots, including Best of Panama (2025) from producer
  Estela Pitti's Finca Los Cenizos, Cerro Punta, Chiriquí.

## Scraping Quirks

- The storefront is localized under `/en`, but canonical product pages are the
  plain `/products/<handle>` form — the scraper strips the
  `/en/collections/all` segment so URLs match the site's real product URLs.
- The `all` collection mixes coffee with branded apparel (T-shirts); those are
  excluded by slug.
- Bean details (blend components, roast level, recommended brew, tasting
  notes) live in collapsed `<details>` accordions rather than in
  `products.json`, so product pages are scraped with the soup pruned to the
  `div.product-information` section.
- The store is IDR-only; the scraper pins `store_currency = "IDR"` so Shopify
  Markets cannot geo-convert prices for datacenter-IP requests.

## Sources

- https://terroiridn.com/
- https://terroiridn.com/en/collections/all
- https://terroiridn.com/products/black-original-omni-roast
- https://www.roastful.com/top-roasters
