---
type: "Reference"
title: "Pilot Coffee Roasters — Roaster Profile"
description: "Toronto roaster born as Te Aro Roasted in 2009, now one of Canada's largest specialty roasters — direct-trade single origins like Ana Sora alongside a core blend lineup, served from a roastery-cafe network across Toronto."
---

# Pilot Coffee Roasters — Roaster Profile

## Overview

Pilot Coffee Roasters is a Toronto-based specialty coffee roaster that began in May 2009 as Te Aro Roasted, a cafe and micro-roastery in the Leslieville neighbourhood opened by Andy Wilkin (a freshly-minted Q Grader) and Jessie Holmes, inspired by the cafes of Te Aro, Wellington, New Zealand (per their site). The Pilot Coffee Roasters name was introduced by 2013, when roasting moved to 50 Wagstaff Drive. Today they operate multiple Toronto cafes plus locations in Oakville and Waterloo, supply wholesale and grocery partners coast to coast across Canada, and ship online orders across North America. Their range pairs single origins (e.g. Ana Sora — Ethiopia, Kii — Kenya, Ruby — Costa Rica) with core blends (Heritage, Monument, Academy, Community) and a decaf blend (Catalyst).

## Address

- Roastery (Roastery Tasting Bar): 50 Wagstaff Drive, Toronto, ON, M4L 3W9, Canada

## Sourcing & Transparency

Pilot publishes a direct-trade sourcing approach on its Coffee Sourcing page (per their site): buying directly from producers with "no brokers, traders or middle-people," qualifying every coffee relationship against four pillars — Quality (distinctive attributes, consistent screen size, 9–10.75% moisture), Transparency (open conversations about costs and pricing, honouring commitments), Environmental (responsible water and land use, sustainable farm practices), and Social (worker health and safety, living wage, gender equity, educational support). No per-bag FOB or farm-gate price figures are published on product pages.

## Schedules & Shipping

- The roastery and production facility operates Monday–Friday (excluding public holidays); Canada-wide orders placed before 3pm EST ship the following business day, later orders within 2 business days (per their shipping policy).
- Estimated delivery once shipped: Ontario + Quebec 1–2 days; Manitoba, New Brunswick, Nova Scotia + PEI 3–4 days; British Columbia, Alberta, Saskatchewan + Newfoundland 5–7 days; Northwest Territories, Yukon + Nunavut 5+ days; metropolitan US 5–8 days, rural US 5–7 days (per their site).
- Complimentary shipping on orders of $45 CAD or more (site-wide banner).

## Philosophy & Quirks

- The original Te Aro Roasted cafe operated out of a former car garage and quickly became a hub for Toronto's emerging specialty scene; the "Then + Now" section of their story page shows the brand's evolution (per their site).
- The Pilot Coffee Club is a membership program with member-discount pricing wired into the storefront's product tags.
- A "Brand New Look" page documents a recent rebrand — product pages carry the refreshed visual identity.

## Scraping Quirks

- Single-origin product pages render a Varietal / Process / Altitude / Origin icon band plus tasting notes (e.g. "Strawberry • Yuzu • Juicy") that do not appear in the Shopify `products.json` payload, so the scraper prunes the page to those elements for AI extraction; blends carry tasting notes but omit the icon band.
- The `/collections/coffee` collection also contains instant coffee and a ready-to-drink nitro cold brew — both excluded by slug (`instant`, `nitro`) since they are not whole-bean products. Sampler/tasting-kit products are not excluded; they flow through the `is_tasting_kit` / `requires_review` review queue if introduced.
- Product pages are canonicalised to `/products/<handle>` (no collection segment), matching the site's own link format.

## Sources

- https://pilotcoffeeroasters.com/
- https://pilotcoffeeroasters.com/pages/our-story
- https://pilotcoffeeroasters.com/pages/coffee-sourcing
- https://pilotcoffeeroasters.com/pages/locations
- https://pilotcoffeeroasters.com/policies/shipping-policy
- https://pilotcoffeeroasters.com/collections/coffee
