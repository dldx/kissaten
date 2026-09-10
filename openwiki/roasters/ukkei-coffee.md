---
type: "Reference"
title: "Ukkei — Roaster Profile"
description: "Peckham, London roastery founded 2024 — 'Ukkei' means home in Cantonese; roast-to-order Mondays, fully recyclable packaging and a £3 discount for skipping the postman."
---

# Ukkei — Roaster Profile

## Overview

Ukkei (pronounced "ook-kay", meaning **home in Cantonese**, 屋企) is a London
coffee roastery established in **2024**, describing itself as "a coffee roastery
that embodies the essence of community". It runs a **Brew Bar** in Peckham —
open Thursday–Sunday — under the same roof as the roastery, and hosts occasional
community events for an area "many of whom have roots in coffee-growing
regions". The storefront is BigCommerce, with beans listed by number and name
(e.g. 012 Radiant Baby, 004 Orange Composition).

## Address

- Unit 30, Rye Lane Market, 48 Rye Lane, Peckham, London, SE15 5BY — United
  Kingdom (roastery and Brew Bar share the site; this is also the registered
  office of UKKEI LTD)

## Sustainability

- Fully recyclable/reusable packaging throughout: paper-only paper clips from
  Japan, a UK-printed postcard, an Austrian ColomPac® reusable postal box, a
  250g bag of unbleached EU food-grade kraft paper, and a recyclable PE-based
  mono-material 1kg bag.
- **Roast-to-order** — explicitly adopted to discourage impulse buying: they
  "reject traditional business 'wisdom' that encourages creating desire simply
  to drive sales", and discount the 1kg bag to reduce packaging waste and
  shipping frequency.
- **£3 off with coupon `PICKUP`** for collecting at the Peckham brew bar —
  framed as a deliberate alternative to "free shipping may be tempting, but the
  carbon emissions come at a cost to our future".

## Sourcing & Transparency

- Sourcing principles (per their site): green coffee from trusted importers who
  prioritise ethics and the environment, fostering direct relationships with
  producers and traceability from farm to cup.
- Direct sourcing in practice: a limited Asian bundle was sourced directly by
  Ukkei during farm visits, including a naturally processed Thai lot from a
  Chiang Mai partner and a rare Alishan (Taiwan) lot. No FOB/price-paid figures
  are published.

## Schedules & Shipping

- **Roasted to order on Mondays**; orders dispatched within three working days
  (Mon–Fri, excluding bank holidays).
- **Free UK shipping** (Royal Mail Tracked 48) — no minimum stated; Tracked 24
  and Tracked 24 Signature available at checkout.
- International via UPS, cost calculated at checkout (fuel surcharges may
  change prices); no orders from the United States.

## Philosophy & Quirks

- The name is a homophone promise: "Ukkei" (屋企) means *home* in Cantonese —
  "We hope you feel at home during your time with us."
- Anti-marketing streak: the sustainability page rails against manufactured
  desire, and sold-out beans are archived rather than hidden — a rare
  "everything visible" shop policy.

## Scraping Quirks

- **Sold-out beans move to `/shop/archive/`** (paginated), a separate listing
  from `/shop/`. The scraper crawls both, tracks which URLs came from the
  archive, and forces `in_stock=False` both at first extraction (the site shows
  "Sold Out", which the AI prompt may miss) and in subsequent diffjson updates.
- **Product URLs are root-level slugs** (`https://ukkei.co.uk/<slug>/`, no
  `/products/` path segment), so default URL-pattern matching would reject
  every product; the scraper keys off BigCommerce's `article.card` selector and
  filters by card title instead. Bundles are additionally excluded by name.

## Sources

- https://ukkei.co.uk/
- https://ukkei.co.uk/about/
- https://ukkei.co.uk/sustainability/
- https://ukkei.co.uk/shipping-returns/
- https://ukkei.co.uk/brew-bar/
- https://ukkei.co.uk/limited-asian-bundle-sold-out/
- https://find-and-update.company-information.service.gov.uk/company/15791839
