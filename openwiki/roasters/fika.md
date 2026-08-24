---
type: "Reference"
title: "Fika Coffee Roasters — Roaster Profile"
description: "Multi-award-winning speciality roaster in County Durham on a Squarespace 7.1 storefront — multi-origin and seasonal roasts in 250g/1kg, plus equipment and training courses."
---

# Fika Coffee Roasters — Roaster Profile

## Overview

Fika Coffee Roasters is a multi-award-winning speciality roaster based in County Durham, on a Squarespace 7.1 storefront at fikacoffeeroasters.co.uk. The /coffee collection carries 16 coffee products — Peru Java Finca Lauramarca, Uganda Ibanda, Colombia Rio Bamisa Geisha, Peru Amazonas, Tanzania Ngila Estate, Rwanda Peaberry, Brazil Bom Jesus, Uganda Kyondo, "The Naturals", a seasonal blend, an espresso blend and a Four Best Sellers set — in 250g/1kg at GBP, alongside subscriptions, equipment and digital gift cards.

## Address

- Unit 3B Riverside Industrial Estate, Langley Park, Durham DH7 9TT, County Durham — United Kingdom

## Philosophy & Quirks

- Multi-award-winning (per their site), with a lineup of multi-origin and seasonal roasts.
- Sells Sanremo equipment and runs training courses; positioned as "Built by Bite Hospitality".

## Scraping Quirks

- Squarespace 7.1 — product URLs come from the sitemap at `/coffee/p/<slug>` (the /coffee listing renders products client-side, so no full URLs are recovered from the data-context blob).
- Multi-segment handles exist: `/coffee/p/brazil/bomjesus`, `/coffee/p/uganda/kyondo/natural`, `/coffee/p/rwanda/peaberry`.
- The `coffee-fika-sample-pack` (sample pack) and "Four Best Sellers" are flagged `is_tasting_kit`/`requires_review` (flag, don't exclude); subscriptions and gift cards are excluded.
- Playwright screenshots time out on networkidle → HTML-only fallback used. Currency is pinned to GBP.

## Sources

- https://www.fikacoffeeroasters.co.uk
- https://www.fikacoffeeroasters.co.uk/coffee