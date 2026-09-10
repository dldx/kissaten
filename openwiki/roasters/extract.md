---
type: "Reference"
title: "Extract Coffee — Roaster Profile"
description: "Bristol roastery built on 'Make Coffee Better' — B Corp certified in 2025, vintage Probat roasters rescued from scrap (Bertha, Betty, Bernie), and a chicken-shed origin story."
---

# Extract Coffee — Roaster Profile

## Overview

Extract Coffee Roasters is a Bristol speciality roaster founded in 2007 by
David, Marc and Samantha, who began roasting on James, a modified 10kg Ozturk,
after starting out in a garden shed and then a chicken shed. Today they roast
from the "Roastery Works" in St Werburghs, run a BigCommerce storefront at
[extractcoffee.co.uk](https://extractcoffee.co.uk), and operate further
training spaces in London and Manchester. Their stated mission — **"Make
Coffee Better"** — runs through everything: a hero-coffee range, wholesale,
subscriptions and Nespresso-compatible pods.

## Address

- Roastery Works, Unit 1 New Gatton Road, St Werburghs, Bristol BS2 9SH —
  United Kingdom

## Sustainability

- Certified **B Corporation®** — announced August 2025 after "a year and a
  half of hard work" (per their B Corp blog post and LinkedIn announcement).
- Published their first **Impact Report** in 2024.
- **Grounds Up** initiative supporting a collective of local community
  partners in Bristol.
- Coffee waste recycled into bio-fuels; 100% recyclable paper cups.
- Salvages vintage roasters from scrap and restores them to run more
  efficiently than when new — Bertha has an afterburner that eliminates VOCs
  ("cleaner air for Bristol") and now runs 60% more efficiently than when
  first built.

## Sourcing & Transparency

- A "quality-pays ethos" built on long-term grower relationships — buying
  from the same farmers year after year so they can forward-plan.
- Long-standing partner farms and co-ops featured by name on the sourcing
  page: Sol y Café (Peru), Coopade women-in-coffee co-op (DR Congo), Delmy's
  Liquidambar (Honduras), El Ingenio (El Salvador), Cauvery Peak (India),
  Finca Veracruz (Colombia) and Wahana Estate (Indonesia).
- No published FOB / farm-gate price figures.

## Roasting & Equipment

- Hand-roasting on **vintage Probat roasters rescued from scrap** and
  restored in-house:
  - **Bertha** — 120kg, 1990s Probat, the roastery's workhorse; found as "a
    pile of parts" decommissioned in Bosnia, rebuilt over 4 years, fitted
    with an afterburner, 60% more efficient than new.
  - **Betty** — 60kg, 1955 Probat, rescued in 2010; afterburner added 2020.
  - **Bernie** — 15kg, 1990s Probat (one of an identical pair; the twin
    lives unrestored at the London training space), converted from electric
    to gas; the small-batch roaster for premium coffees.
  - **James** — the original Ozturk, now retired to the wholesale training
    room.

## Schedules & Shipping

- Roasting, picking, packing and shipping **Monday–Friday** (closed bank
  holidays); retail orders dispatched in 1–2 working days.
- **Free Royal Mail Tracked 24® shipping on retail orders over £25.00
  (ex VAT)** and on all subscription renewals.
- Under £25: Royal Mail Tracked 48® £3.50 or Tracked 24® £4.50.
- Wholesale: courier delivery free over £250.00 (ex VAT), otherwise £8.50
  (ex VAT); free local van deliveries to wholesale partners in certain
  Bristol postcodes.

## Philosophy & Quirks

- Motto: **"Make coffee better"** — for drinkers, growers, communities and
  the planet. Their other tagline: "different beats best."
- Started in 2007 in a **chicken shed** before moving to the Roastery Works.
- All roasters are named: Bertha, Betty, Bernie — and James, after the little
  red engine in Thomas the Tank Engine.
- **Betty Espresso** launches every year on International Women's Day and
  champions female coffee growers; it first launched in 2020 to mark ten
  years since Betty's restoration.
- UK Coffee Awards Best All-Round Speciality Roaster 2022 (per Roasterlist /
  day9.coffee).

## Scraping Quirks

- **Mixed product URL paths within one listing**: product URLs mix
  `/shop/<slug>/` (most items) and legacy `/coffee/<slug>/` paths (e.g.
  Strangelove) in a single category listing. The only selector that reliably
  captures both is the BigCommerce Stencil card link `a.sf-productCard`;
  broader selectors like `a[href*="/coffee/"]` can return as little as one
  URL on the hero-coffees page.
- **Non-coffee exclusions**: coffee pods and the gift subscription are
  filtered out of the product list explicitly (plus a general `/gifts/`
  guard).

## Sources

- https://extractcoffee.co.uk/
- https://extractcoffee.co.uk/about-us/
- https://extractcoffee.co.uk/sustainability/
- https://extractcoffee.co.uk/environmentally-friendly-coffee/meet-the-roasters/
- https://extractcoffee.co.uk/sustainability/ethical-coffee-sourcing/
- https://extractcoffee.co.uk/support/shipping-returns/
- https://extractcoffee.co.uk/contact/
- https://extractcoffee.co.uk/blog/were-officially-a-certified-b-corporation/
