---
type: "Reference"
title: "Sacred Mill — Roaster Profile"
description: "Nairobi-and-Warsaw specialty roaster born from a chance encounter with a Kenyan coffee farmer — direct sourcing, a Colombian processing HQ, and a Rare series of co-fermented geishas."
---

# Sacred Mill

## Overview

Sacred Mill Specialty Coffee is a roaster founded by "global nomads with African and Asian roots" who entered coffee via a chance encounter with a Kenyan coffee farmer. They imported their first directly traded Kenyan specialty coffee to Poland in 2019, opened a flagship brew bar in Warsaw in 2020, and formally became Sacred Mill Coffee Roasters in February 2021 (per their site). Today they operate from Nairobi, Kenya (Sacred Mill Kenya Limited) with roasting/brew-bar locations in Warsaw, Poland — Grzybowska 43A and Kamionkowska 9/U3, Kamionek — and a café in Mwanzi Market, Westlands, Nairobi. Their beans are sold in Roots, Renaissance and Rare series, and the online store runs on Shopify with the Polish złoty (PLN) as base currency across all its storefront markets.

## Address

- Sacred Mill Kenya Limited, Springvalley, Westlands District, West of Nairobi, 00-606, Kenya (per their contact page); Warsaw roasting lab at Przecławska 5, Building 4, Unit Ł, 03-879 Warszawa, Poland (per their contact page).

## Sourcing & Transparency

- Ethical sourcing is the founding story: they state they import and source specialty green coffee "through like-minded partners" while ensuring fair pay to farmers and transparency across the supply chain (per their Our Story page).
- Unusually for a roaster, they run their own processing HQ — Los Patios in Gigante, Huila, Colombia — where their R&D team develops co-fermentation lots (e.g. their "Scarlet" red-fruit process), buying de-pulped cherries from smallholder producers with farms of roughly 1,600–1,900 m.a.s.l. averaging 3 ha (per their product pages).
- Product pages publish per-coffee detail: Flavor Profile, Cup Score (e.g. 88.00), Terroir, Producers, Altitude and Variety.

## Philosophy & Quirks

- Catalogue is organised in three named series: **Roots** (approachable single origins), **Renaissance** (statement lots, 250–500 g) and **Rare** (small high-scoring lots such as Panama Geisha and Colombia Gesha, 150–200 g).
- They also sell "Coffee Spirits" — a Sage & Elder coffee liqueur collaboration — alongside a small merch line.
- Product pages carry a "Roaster's Signature" essay describing each lot's processing story rather than marketing blurbs.

## Scraping Quirks

- **The roaster is Kenyan but the store's base currency is PLN**: the Shopify storefront serves every market (Poland, Czechia, Estonia, Germany, Slovakia) in PLN and the products.json rate is 1.0. The scraper pins `store_currency = "PLN"` so geo-converted prices cannot leak in.
- There is **no curated coffee collection** — coffee is split across filter/espresso/rare/renaissance/roots/drip-bags collections, so the scraper uses `collections/all` and excludes merch, spirits and green coffee by slug (drip bags stay in).
- The structured bean detail (Flavor Profile, Cup Score, Terroir, Producers, Altitude, Variety, Process) lives in page metafields **not** present in products.json, so product pages must be scraped; the soup is pruned to the theme's `__main` section.
- The live Shopify store was frozen (HTTP 402 "This store is currently unavailable") at the time the scraper was written; the site structure and currency were verified via Wayback Machine snapshots (2024–2025). If scraping fails with 402, the store is likely still suspended.

## Sources

- https://sacredmill.coffee/ (store, currently frozen — verified via Wayback Machine snapshots from 2024–2025)
- https://web.archive.org/web/20210619155948/https://sacredmill.coffee/pages/our-story
- https://web.archive.org/web/20240614094004/https://sacredmill.coffee/pages/locations
- https://web.archive.org/web/20251018143349/https://sacredmill.coffee/collections/all
- https://sacredmill.coffee/policies/contact-information (per live-site search result quotes)
- https://sacredmill.coffee/products/rare-filter-colombia-los-patios-200g (verified via Wayback Machine snapshot, 2025)
