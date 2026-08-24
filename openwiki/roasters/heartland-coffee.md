---
type: "Reference"
title: "Heartland Coffee Roasters — Roaster Profile"
description: "North Wales (Llandudno) roaster on Shopify at heartland.coffee — roasting since 2005 after New Zealand founders Mal & Tara moved from London, with 19 coffees (17 single origins, the Landmark blend, Swiss Water decaf) and a roastery + coffee bar in Llandudno."
---

# Heartland Coffee Roasters — Roaster Profile

## Overview

Heartland Coffee Roasters is a North Wales speciality roaster on a Shopify
storefront at heartland.coffee (heartlandcoffee.co.uk 301s to it). Mal & Tara
started roasting in their London flat after emigrating from New Zealand,
going commercial in 2005 and relocating the roastery to Llandudno in 2012.
The curated coffee collection holds 19 products — 17 single origins, the
Landmark blend (their cornerstone for 15+ years) and a Swiss Water decaf
blend — sold from a roastery + showcase coffee bar in Llandudno.

## Address

- Unit 6 & Unit 8, Cwrt Roger Mostyn, Builder Street, Llandudno LL30 1DS — United Kingdom.

## Sourcing & Transparency

- Sourcing page: direct relationships with producers and fair prices —
  trading directly with farmers and committing to whole crops or micro-lots
  where possible; other coffees come from regional cooperatives (per their site).
- Ethos of "sourcing responsibly, paying fairly"; no per-kg price
  transparency published.

## Schedules & Shipping

- UK-only shipping via DPD (tracked), dispatched within 3 working days of
  order; no free-delivery minimum published on the delivery page.

## Philosophy & Quirks

- Tagline "Roasted in North Wales"; moto "Coffee, Craft and Community" — the
  move to Llandudno rode the rise of the North Wales independent coffee scene.
- Landmark is the cornerstone house blend, celebrated for balance and a
  chocolatey finish for over 15 years.

## Scraping Quirks

- Shopify; only the curated `coffee` collection is crawled (19 products);
  `single-origin` (17) is a strict subset — no merge.
- JSON-only: the structured spec table (Country, Region, Producer, Altitude,
  Varietal, Process, Cupping Notes) lives in products.json `body_html`; page
  scraping is skipped.
- No `roast_level` anywhere — the field is null for every product.
- Canonical domain is heartland.coffee (heartlandcoffee.co.uk 301s); URLs canonicalise to `/products/<handle>`.

## Sources

- https://heartland.coffee
- https://heartland.coffee/pages/about
- https://heartland.coffee/pages/sourcing
- https://heartland.coffee/pages/delivery
- https://heartland.coffee/pages/visit
