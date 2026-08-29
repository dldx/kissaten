---
type: "Reference"
title: "Mission Coffee Works — Roaster Profile"
description: "London specialty coffee roaster and direct-sourcing importer on Shopify, selling in GBP with free UK delivery over £25 and annual Impact Reports covering carbon, sourcing and social impact."
---

# Mission Coffee Works — Roaster Profile

## Overview

Mission Coffee Works (missioncoffeeworks.com) is a London-based specialty
coffee roaster and importer on a Shopify storefront priced in GBP. It sources
direct micro-lot coffees from around the world and roasts them "ethically" in
the UK (per their site), selling single origins, espresso and filter blends,
Taster Packs, gift subscriptions, tea and brewing equipment. The company
publishes annual Impact Reports — a "2025 Impact Report" and a "2024 Impact
Report - July Update" — from the site's Journal, covering environmental,
social and economic impact.

## Address

- Unit 6 Queen's Yard, London, E9 5EN — United Kingdom (per their contact
  page).

## Sustainability

- **Carbon accounting**: the 2025 report commissioned carbon-emission experts
  Climabrite to calculate Scope 1/2/3 emissions; Scope 3 was by far the
  largest — upstream coffee and packaging purchasing, downstream delivery
  (APC, DPD, Royal Mail), coffee-machine energy use and packaging waste (2025
  report, pp7–8). A July 2025 update to the 2024 report published the
  Climabrite baseline: Scope 1 6.33, Scope 2 7.74, Scope 3 upstream 78.92,
  downstream 66.48, total 159.47 tCO2e (July 2025 update, p1).
- **Green utilities**: in June 2025 Mission obtained a British Gas Zero
  Carbon Certificate confirming 100% of its electricity is backed by
  renewable-energy guarantees of origin and nuclear declarations through
  2028, saving 6.7 tonnes of CO2 since switching to green energy; gas supply
  and water use still need work (2025 report, pp4, 8). The July 2025 update
  adds that after moving to new premises in Hackney Wick in early July, the
  roastery runs on 100% renewable energy (July 2025 update, p1).
- **Packaging & waste**: no coffee-bag alternative has yet met both quality
  and cost requirements, so the wholesale circular bucket system keeps
  expanding — 800 kg of waste diverted from landfill in 2025 (2025 report,
  p4); customer bag returns are being investigated and refillable retail
  options are planned for the 2026 retail space (p8). Talks with Hackney
  Wick-based Fibre Lab began in late 2025 to repurpose the ~15 coffee sacks
  used per week and the coffee chaff from roasting (p9).
- **2024 milestones** (2024 report, pp4–7): ~40% of weekly dispatches in
  circular buckets, a larger electric delivery van, fully recyclable paper
  tape replacing acrylic (~400 m of tape/week; ~9,200 m less acrylic
  estimated), 655 kg of waste diverted, 0% of roasting by-product to landfill
  (chaff composted via the food-waste bin with Biffa), and refillable 20 L
  cleaning containers avoiding ~44 single-use bottles. Coffee bags are sourced
  from China and recyclable through local supermarket soft-plastics schemes,
  with limited visibility into manufacturing practices (p8).

## Sourcing & Transparency

- **Price transparency** (2025 report, p16): Mission paid on average more
  than 80% above the C-market price for all green coffee contracted in 2025 —
  explicitly an FOB-vs-C-market comparison, not a verified
  farmgate/producer-payment figure. Farmgate prices are typically estimated
  at 60–80% of FOB, but exact figures were unavailable for most import
  partners.
- Four coffees came from sourcing partnerships longer than three years (2025
  report, p4); sourcing countries shown include Guatemala, Honduras, China,
  Peru, Brazil, Panama, Costa Rica, Papua New Guinea, Colombia, Ethiopia,
  Kenya, Uganda and Rwanda (p5).
- **Producer relationship** (2024 report, p17): the Brazilian component of
  the house blend Bells is ~75% of total roasting volume; a direct
  relationship with Vini Silva of UPC (União de Produtores de Café) in Minas
  Gerais — UPC registered in both Brazil and the UK — cuts out the exporter
  intermediary and supports ~200 coffee producers.
- **The Stumping Project**: £5 per kg of Lalesa (the 2024 Ethiopian festive
  coffee) was committed to the project, which provides stumping tools and
  training — stumping causes farmers a ~1.5-year income gap while trees
  regrow (2024 report, p18). The 2025 report notes the £5/kg-sold commitment
  carried over from the prior Christmas coffee (p17).
- **The Indian Coffee Project**: begun in late 2025 with producers in
  Meghalaya, north-east India, to revive specialty production there; Mission
  committed to buy six sacks of the first harvest as a long-term project (2025
  report, pp17–19).
- Self-described roaster *and* importer sourcing direct micro-lot coffees
  from around the world (per their site); the reports are the primary public
  source of price and producer-payment data.

## Schedules & Shipping

- Free delivery for orders over £25 (site banner); no roasting/dispatch
  cadence published.

## Philosophy & Quirks

- Mission: "create progress for our people, our community, and the coffee
  industry as a whole", built on the three Ps — people, passion, progress —
  with a "People over Profits" mantra (2024 report, pp1–2, 12).
- Social impact highlights: 2025 — 35 volunteer hours, 25 people directly
  impacted, 100+ hours training wholesale customers, and a team NPS of 50
  (2025 report, pp4, 13); charity partnerships with Well Grounded and
  FairShot, including mentoring of programme graduates (pp11–12). 2024 —
  106 hours of team training/upskilling, four new team members, and three
  staff working toward an SCA Sustainability qualification (2024 report,
  pp11–12).
- Honest reporting: the 2025 report concedes it did not achieve its 2025
  goals of funding a new educational project at origin and releasing two
  charity coffees, and sets 2026 goals of a closed-loop packaging solution
  outside London, DEI policies, and launching the Indian Coffee Project (2025
  report, pp17, 20).

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
- https://missioncoffeeworks.com/pages/impact-report (Impact Report landing page)
- https://cdn.shopify.com/s/files/1/0247/7457/4157/files/Impact_Report_2025.pdf?v=1777635188 (2025 Impact Report)
- https://cdn.shopify.com/s/files/1/0247/7457/4157/files/Impact_Report_2024.pdf?v=1736866815 (2024 Impact Report)
- https://cdn.shopify.com/s/files/1/0247/7457/4157/files/Impact_report_2024_update.pdf?v=1753460341 (July 2025 update)