---
type: "Reference"
title: "Mission Coffee Works — Roaster Profile"
description: "London specialty coffee roaster and direct-sourcing importer on Shopify, selling in GBP with free UK delivery over £25 and publishing annual Impact Reports."
---

# Mission Coffee Works — Roaster Profile

## Overview

Mission Coffee Works (missioncoffeeworks.com) is a London-based specialty
coffee roaster and importer on a Shopify storefront priced in GBP. It sources
direct micro-lot coffees from around the world and roasts them "ethically" in
the UK (per their site), selling single origins, espresso and filter blends,
Taster Packs, gift subscriptions, tea and brewing equipment. The company
publishes annual Impact Reports (2025, 2024) from the site's Journal.

## Address

- Unit 6 Queen's Yard, London, E9 5EN — United Kingdom (per their contact
  page).

## Sourcing & Transparency

- Self-described roaster *and* importer sourcing direct micro-lot coffees
  from around the world (per their site).
- Publishes annual Impact Reports ("2025 Impact Report", "2024 Impact Report
  - July Update") covering the business's social/environmental impact.

## Schedules & Shipping

- Free delivery for orders over £25 (site banner); no roasting/dispatch
  cadence published.

## Scraping Quirks

- Shopify products.json: `product_type == "Coffee"` keeps 27 coffee-classed
  products, then slug-exclusion removes subscription products — the 12/6/3
  month term-variant duplicates (`*-12-months`, `*-6-months`, `*-3-months`)
  and the ongoing `coffee-subscription-*` rows — leaving the base beans.
- Taster/selection products are NOT excluded: the "Roaster's Espresso
  Selection" sample flows through and is kit-flagged (`is_tasting_kit` /
  `requires_review`) for the admin review queue.
- Rich `body_html` means JSON-only extraction (`scrape_product_pages=False`).
- A ~£11 "Cold Brew Kit" and filter/equipment products failed Gemini
  extraction on the first run and are re-tried on subsequent sessions.

## Sources

- https://www.missioncoffeeworks.com
- https://www.missioncoffeeworks.com/pages/contact-us