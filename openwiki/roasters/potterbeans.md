---
type: "Reference"
title: "Potterbeans — Roaster Profile"
description: "Cornwall (UK) wood-roasted coffee roastery with hand-thrown pottery at the canonical potterbeans.coffee domain, solar-dried Cornish oak fuel, sail-shipped coffees, a dynamic 41-bean all-coffee catalogue, and free UK shipping over £50."
---

# Potterbeans — Roaster Profile

## Overview

Potterbeans (potterbeans.coffee, not .co.uk) is a Cornwall, UK roastery that
pairs wood-roasted coffee with hand-thrown pottery, selling through a Shopify
storefront in GBP. The whole-bean catalogue (`all-coffee`) carries single
origins, blends and decaf plus curated tasting samplers and subscription
options. The roastery's two vintage machines — a 1950s FIMT and a 1940s UNO —
are fired on solar-dried Cornish oak, and the beans are roasted freshly after
ordering. No founding year is published on the site.

## Address

- The site's FAQ directs local-pickup customers to **Blackwater TR4 8HW, near
  Truro** (no full street address is published; the FAQ links a map for the
  exact location).
- Cornwall, England — United Kingdom.

## Sustainability

- **Wood fuel**: the primary FIMT roaster, built in the 1950s to run on gas
  and/or wood, is run on **solar-dried Cornish oak**. The roastery's site
  describes this as "an almost carbon-neutral coffee roasting fuel" — a
  self-description, not an audited carbon-neutral claim (no audit or
  certification is published).
- **Working Woodlands Cornwall CIC** (workingwoodlandscornwall.com), a
  community interest company "right on our doorstep", supplies the oak. They
  dry wood in a solar kiln (speeding natural drying from ~2 years to ~3
  months without burning fuel), use ancient coppicing with a staggered harvest
  cycle, set aside ~50 large standard oaks for biodiversity, and preserve
  ancient woodland with public footpath access.
- **Packaging**: all coffee ships in compostable paper packaging with a
  biodegradable starch lining; "with no plastic valves it is plastic free"
  (per the FAQ). Bags carry a roasting date; coffee is best used fresh,
  within ~3 weeks of roasting.
- **Sail coffees**: a dedicated "Sail Coffees" line is transported by **TOWT
  (TransOceanic Wind Transport)** and sourced by **BELCO**, with the site
  noting the beans are "not sailed directly to our door" — the roastery says
  it is invested in growing this mode of transport (motivated by reducing CO2,
  marine noise pollution and switching to renewable energy).

## Sourcing & Transparency

- The site's **Farms & Producers** blog is the primary public transparency
  surface, with producer spotlights (the below details are as described by the
  roastery's own posts, not independently verified).
- **Rafael Amaya** (Colombia): a producer spotlight (Oct 2022) profiles a
  farmer who began as a picker, bought his own farm in 2000, and developed
  long-fermentation washed lots (from ~40 hours up to 130–180 hours) dried in
  GrainPro bags and on shaded patios. The post presents this as a coffee the
  roastery proudly supports; note the spotlight predates the current catalogue
  snapshot, so the referenced product may not be currently listed.
- **Karst Organics** (East Timor): a Feb 2026 post profiles the exporter/
  importer founded by Stewart and Kar-Yee after a 2017 visit to Letefoho. Per
  the post, Karst built a processing facility to partner directly with local
  farmers, guarantees minimum prices ($0.85/kg for cherries, $4.00/kg for
  parchment), registers all staff formally, and acts as both exporter and
  importer for supply-chain transparency. East Timor coffees
  (`east-timor-remagoa`, `east-timor-rotutu`, `east-timor-twin-pack`) appear in
  the current catalogue.
- The roastery does not publish price-transparency or
  producer-payment figures of its own; sourcing detail lives in the blog
  spotlights rather than on product pages.

## Roasting & Equipment

- **FIMT** — the primary roaster, built in the 1950s, originally dual-fuel
  gas/wood, now fired on solar-dried Cornish oak.
- **UNO** — built in the 1940s, with a roasting drum open to the air for a
  "sight, sound, and smell" connection to the roast; used for sample-roasting
  speciality/experimental coffees before moving to larger wood-roasted batches.
- Small-batch, quality-over-quantity approach: the softer, higher-moisture
  wood heat retains more natural oils for a smooth, full-bodied cup and
  reduces scorching/bitterness. The site frames wood roasting as the
  age-old method that "fell out of fashion in the late 19th and early 20th
  century" with the rise of gas/electricity, which it revives sustainably.

## Schedules & Shipping

- **Standard UK delivery is £4** on all UK orders, shipped via **Royal Mail**,
  "will usually take 2-4 working days to arrive" (shipping policy).
- Caveats: the FAQ adds that orders ship with Royal Mail 24hr delivery and,
  "although usually shipped same day, it can take 2-4 working days **before
  dispatch**, depending on the roasted coffee inventory" — so the 2–4 day
  window can include dispatch lead time, not just transit.
- **Wood-fired roasts are shipped on a Thursday** (shipping policy).
- Free UK shipping on orders over **£50** (cart banner: "You're £50.00 away
  from FREE SHIPPING!").
- International delivery: "more coming soon" — contact
  sales@potterbeans.coffee.
- Local pickup available at Blackwater TR4 8HW near Truro (see map).
- **Subscriptions**: monthly, home delivery only. First order is dispatched
  within 2–4 days depending on roasting days; subsequent orders arrive
  monthly on the anniversary of the first order, chargeable monthly from signup
  and manageable/cancellable from the account's subscription section. Options
  include "Roasters Choice" (from £7.50) and the "Speciality Mixed Box"
  tins subscription (£25.00).

## Philosophy & Quirks

- Core pairing: wood-roasted coffee with hand-thrown pottery, sold together in
  gift sets as well as separately.
- **The potters**: resident potter **Lucy Brown** makes all pottery pieces at
  the roastery, drawing on coastal colours and slips (she also runs
  babalupottery.co.uk); a second blog, "The Potters", features **Laurence
  Eastwood**. Pottery is dishwasher- and microwave-safe.
- Stated goal: "bring people the best brew possible" while doing so "with as
  little environmental impact as possible" — the combination that led to
  wood roasting.
- Reviews (Judge.me on-site) repeatedly note freshly roasted beans ("roasted
  the day after I ordered") and the packaging's giftability/recyclability.

## Scraping Quirks

- Canonical domain is potterbeans.**coffee** (the checklist's `.co.uk` is
  stale — a domain correction; `.co.uk` redirects 301).
- **Dynamic catalogue snapshot**: the curated `all-coffee` collection
  (`/collections/all-coffee/products.json`) is the union of the roaster's
  single-origin, blend and sail-coffee collections and currently returns **43
  published products** (40 typed `Coffee`, 3 typed `coffee`). Two genuine
  recurring-subscription products (`speciality-coffee-tins-subscription`,
  `coffee-of-the-month`) are excluded by slug, landing **41 beans** — the
  count drifts over time as products are added/removed.
- **Shopify JSON-only extraction**: `body_html` carries the bean details, so
  the scraper uses the cheapest path — `scrape_product_pages=False`,
  `use_optimized_mode=True`, no page caching.
- **Sampler review flags** (flag-don't-exclude): the `gift-box-of-5-coffee-tins`
  sampler is caught by the base `_apply_product_flags` (`gift-box` URL) and
  flagged `is_tasting_kit`/`requires_review`; curated multi-bag twin packs
  (`anaerobic-and-super-natural-twin-pack`, `co-ferment-speciality-twin-pack`,
  `east-timor-twin-pack`) are flagged via `postprocess_review_flags`. All land
  in the admin review queue, never excluded.
- Canonical product URLs are the no-collection form `/products/<handle>`; the
  `/collections/all-coffee` segment injected by the products.json base is
  stripped in `preprocess_product_url`.
- Store currency is pinned to GBP (the storefront can geolocate datacenter IPs
  to a non-GBP market).

## Sources

- https://potterbeans.coffee
- https://potterbeans.coffee/pages/wood-roasted-coffee (About the Roastery)
- https://potterbeans.coffee/pages/our-pottery (About the Pottery)
- https://potterbeans.coffee/pages/working-woodlands
- https://potterbeans.coffee/pages/faq
- https://potterbeans.coffee/policies/shipping-policy
- https://potterbeans.coffee/pages/contact-us
- https://potterbeans.coffee/collections/all-coffee
- https://potterbeans.coffee/collections/shipped-by-sail
- https://potterbeans.coffee/blogs/farms-and-producers
- https://potterbeans.coffee/blogs/farms-and-producers/karst-organics
- https://potterbeans.coffee/blogs/farms-and-producers/farmer-spotlight-rafael-amaya
- https://workingwoodlandscornwall.com (Wood supplier, linked from the Working Woodlands page)