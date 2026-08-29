---
type: "Reference"
title: "Volcano Coffee Works — Roaster Profile"
description: "South London speciality coffee company founded by Kiwi chef Kurt Stewart from a Piaggio Ape coffee cart, now a B Corp-certified Shopify roaster with Loring roasters, a Brazilian agroforestry project and barista courses at its Brixton HQ."
---

# Volcano Coffee Works — Roaster Profile

## Overview

Volcano Coffee Works (volcanocoffeeworks.com) is a South London speciality
coffee company on a Shopify storefront, founded by New Zealander and former
chef Kurt Stewart. The official story is that it started with a vintage
Italian Piaggio Ape coffee cart serving Full Steam Espresso from the footpath
in West Dulwich; the independent Standard profile corroborates that Full Steam
Espresso began in **2007** and that investment in **2010** enabled scaling. The
site says the company now has a London roastery, a café and a 56-person team,
and that Kurt still roasts the first batch of the day (per the site). The range
covers blends, single origins, decaf, compostable pods, cold brew, barista
bags, subscriptions, equipment, gifts and barista courses. Its All Coffee
collection currently lists 33 products — a mix of coffee-type beans, pods and
subscriptions, not a bean count.

## Address

- No single roastery street address is published. The site's official HQ,
  offices and barista-training academy is the **Door Coffee Bar, 244 Ferndale
  Road, Brixton, London SW9 8FR — United Kingdom**, a café collaboration with
  Assembly Coffee.
- The company's own café is in West Norwood (SE21 8EN; full street number not
  published). Site copy associates the roasting operation with Brixton (e.g.
  "we don't fill the air around Brixton with smoke") rather than asserting one
  definitive roasting site; a historical Standard profile described roasting
  across a Brixton site and a West Dulwich warehouse base.

## Sustainability

- **B Corp**: the site says Volcano has been a Certified B Corporation since
  2021 and cites a 2024 B Impact Score of 93.1 (2021: 84). These are
  site-claimed figures, not independently verified here.
- **Environmentally Better page**: Loring roasters use **80% less gas** than
  conventional roasters and are smokeless; packing wholesale coffee in larger
  bags saves over 150 kg of plastic a year; packaging is "100% recyclable" with
  50% recycled material; Nespresso-compatible pods are described as fully
  compostable.
- **Compostable pods**: the pod page claims plant-based/cornstarch pods, OK
  Compost Home certification and 180-day degradation — but the same page also
  describes them as industrially compostable. Both are site wording; they are
  not reconciled here.
- Other site claims: refill dispensers, FirstMile recycling/waste systems and
  cycle-based initiatives.
- **Carbon-neutral caveat**: a legacy footer badge and older press copy (e.g.
  Time Out) describe Volcano as "carbon neutral", but the official
  `/pages/carbon-neutral` page returns 404 and no current carbon accounting or
  offset documentation was found. Treat "carbon neutral" as legacy wording, not
  a current verified claim.

## Sourcing & Transparency

- **Ethically Better page**: long-term fixed-price buying contracts with farms;
  farmers paid above Fairtrade/commodity benchmarks — the site says "on average
  double that of Commodity Coffee (C Market) and Fair Trade" — and product pages
  claim 50–180% above Fairtrade. These are company/product claims, not
  independently audited figures.
- **Supplier policy**: a published code of conduct requires no forced or child
  labour, origin disclosure, environmental impact reduction, and
  grievance/audit/corrective-action processes; the sourcing pillars are
  sustainable livelihoods, environmental good and social progress.
- **Sombra Project**: a 5-year agroforestry project in Brazil with green-coffee
  partner Fazenda Mió and the Universidade Federal do Espírito Santo — a ~15 ha
  plot planned for over 60,000 trees and coffee plants, funded by premiums on
  coffee sales (per the site). No independent monitoring or outcome data is
  published.

## Roasting & Equipment

- Current **Environmentally Better** page: **Loring roasters**, using 80% less
  gas than conventional roasters, smokeless, small-batch.
- Historical (2018 Standard profile, labelled as such): small batches of
  25–30 kg, up to ~30 roasts a day, roughly 800 kg/day.
- Product pages say coffee is freshly roasted to order / sent within ~10 days
  of roasting (per product pages). No current carbon-neutral production claim is
  made here.

## Schedules & Shipping

- **Roasting**: the shipping page says coffee is freshly roasted every day.
- **Dispatch**: orders before midnight Monday–Thursday are dispatched the next
  working day; Friday orders go out Monday (excluding bank holidays); DPD orders
  before 12pm may dispatch the same day.
- **UK rates** (per the shipping page): Royal Mail Tracked 2–4 working days —
  £3.45 under £25, £2.45 between £25–£45, free over £45; DPD 2 working days —
  £6. Free UK mainland delivery on orders over £45 and on all subscriptions.
- **International**: generally £10–£20 depending on destination.
- **Taste Guarantee**: first 200g coffee purchase — replacement (1×200g) or
  refund, subject to the published terms.

## Philosophy & Quirks

- Founder's story: a Kiwi chef who blends coffee "like a sauce, a meal, or a
  wine" — the chef's perspective on flavour is a recurring brand motif.
- **Barista courses** at the Brixton HQ: home espresso, Sage espresso, latte
  art, coffee tasting, private and student barista classes (typically ~2.5
  hours, per the site).
- **Subscriptions**: whole-bean or ground, espresso or filter; delivery every
  2/4/6 weeks with pause/skip/cancel; 15% off the first three orders with code
  DISCOVER15; a Roaster's Choice subscription sends 500g/1kg every four weeks.
  Offer detail is volatile — treat as a snapshot.
- **Products**: The Mount Blend (Brazil/El Salvador/Colombia, medium, milk
  chocolate/caramel/red grapes; product page claims a 3-star Great Taste award);
  Sombra (Brazil, natural; product page claims a 1-star Great Taste award); the
  Speciality Coffee Starter Box contains The Mount Blend, The Brixton and Sombra
  (3×200g) plus a coffee tin. Awards are product-level claims only.

## Scraping Quirks

- Shopify products.json at `/collections/buy-volcano-coffee/products.json`; the
  store currency is pinned to GBP so Shopify Markets geolocation can't override
  the roaster's home currency.
- Filters on `product_type == "Coffee"`, then excludes handles containing
  `gift`, `cold-brew` and `bag` (gift sets, cold-brew cans/concentrate and
  barista coffee bags that Shopify still classes as Coffee).
- Tasting/sampler kits are intentionally **not** excluded: the Speciality
  Coffee Starter Box and Roaster's Choice are retained and flagged
  `is_tasting_kit` / `requires_review` for the admin queue.
- Product URLs are canonicalised to `/products/<handle>` (the collection
  segment is stripped from the products.json URLs).
- Catalogue size is volatile (the All Coffee collection currently mixes 22
  Coffee-type products with pods and subscriptions) — don't hardcode counts.

## Sources

- https://volcanocoffeeworks.com
- https://volcanocoffeeworks.com/pages/who-we-are
- https://volcanocoffeeworks.com/pages/contact
- https://volcanocoffeeworks.com/pages/door-coffee-bar
- https://volcanocoffeeworks.com/pages/environmentally-better
- https://volcanocoffeeworks.com/pages/b-corp
- https://volcanocoffeeworks.com/pages/our-commitments
- https://volcanocoffeeworks.com/pages/better-ethically
- https://volcanocoffeeworks.com/pages/supplier-policy
- https://volcanocoffeeworks.com/pages/supplier-code-of-conduct
- https://volcanocoffeeworks.com/pages/sombra
- https://volcanocoffeeworks.com/products/sombra
- https://volcanocoffeeworks.com/products/the-mount-blend
- https://volcanocoffeeworks.com/products/speciality-coffee-starter-box
- https://volcanocoffeeworks.com/pages/shipping
- https://volcanocoffeeworks.com/pages/taste-guarantee
- https://volcanocoffeeworks.com/pages/home-barista-courses
- https://volcanocoffeeworks.com/pages/volcano-home-compostable-coffee-pods
- https://volcanocoffeeworks.com/collections/all-coffee
- https://www.standard.co.uk/going-out/foodanddrink/kurt-stewart-volcano-coffee-interview-made-in-london-a3815271.html (historical corroboration: 2007/2010 origin, 2018 batch figures)
- https://volcanocoffeeworks.com/pages/carbon-neutral (legacy — returns 404; cited only to document the broken carbon-neutral page)