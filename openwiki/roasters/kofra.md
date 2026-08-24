---
type: "Reference"
title: "Kofra Coffee — Roaster Profile"
description: "Norwich specialty roaster on a Wix storefront with a tiny three-bean catalogue — Joy seasonal blend, Espirito Santo Brazil natural and Los Nogales decaf — roasted to order and sold from three city cafés."
---

# Kofra Coffee — Roaster Profile

## Overview

Kofra Speciality Coffee Roasters (www.kofra.co.uk) is a Norwich specialty
coffee roaster on a Wix storefront in GBP with a deliberately tiny
three-bean catalogue: Joy (an everyday seasonal blend, washed Huila Colombia),
Espirito Santo (Brazil ES natural) and Los Nogales decaf, all in 250g.
Coffee is freshly roasted to order, whole bean or ground, and sold from three
Norwich cafés.

## Address

- 16 Onley Street, Norwich, NR2 2EB — United Kingdom (café).
- 81 Upper St Giles, Norwich, NR2 1AB — United Kingdom (flagship café, central
  bakery and online-sales distribution hub; opened February 2020).
- 1 Bell Road, Norwich, NR3 4RA — United Kingdom (café; opened summer 2020).
- No separate roastery address is published on site.

## Sustainability

- All takeaway cups and one-use items are fully compostable (per their FAQ).

## Sourcing & Transparency

- States it maintains strong relationships with producers and profiles them on
  the site (Nestor Lasso, La Cristalina, Diego Samuel) (per their site).

## Schedules & Shipping

- Coffee is roasted to order (per their FAQ).
- Orders before 10 am ship the same day; orders after 3 pm Friday are posted
  Monday/Tuesday. Sent Royal Mail First Class, usually arriving in 2–4 working
  days.
- Delivery £4.25; free for orders of £36 and over.

## Scraping Quirks

- Wix storefront, not Shopify — no `products.json`.
- Sitemap-driven discovery: `store-products-sitemap.xml` lists exactly the
  three products (verified complete; no other product sitemap exists).
- Product pages are narrowed to the `<main>` (PAGES_CONTAINER) element —
  ~1.5 MB page reduced to ~16.5 KB before extraction.
- Availability is read from `meta[property="og:availability"]` (not
  `product:availability`) and re-injected into the narrowed soup.
- Currency pinned to GBP; canonical www.kofra.co.uk/product-page/<slug>.

## Sources

- https://www.kofra.co.uk
- https://www.kofra.co.uk/shipping
- https://www.kofra.co.uk/about-us
- https://www.kofra.co.uk/store-products-sitemap.xml
