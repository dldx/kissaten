---
type: "Reference"
title: "Harmony Coffee — Roaster Profile"
description: "York (North Yorkshire) nano specialty roastery run by barista-champion Ben Rowe (Just Bru Ltd) — single origins roasted on a Loring S15, 300+ UK wholesale accounts and flexible subscriptions on Shopify."
---

# Harmony Coffee — Roaster Profile

## Overview

Harmony Coffee is a nano specialty coffee roastery in York, North Yorkshire
(United Kingdom), owned and operated by Ben Rowe as part of Just Bru Ltd
(co-owned by Livi Collins). It positions itself as a wholesale specialty
roaster — "trusted by over 300 businesses around the UK" — selling single
origins, flexible coffee subscriptions and wholesale support from a Shopify
storefront in GBP. The About page says Harmony grew from a desire to bring
modern coffee roasting to York, built around four pillars: Traceability,
Quality, Ethics and Partnership. Site references such as the Micafe
partnership ("since Harmony's inception in 2022") point to a 2022 inception,
though the site publishes no formal incorporation date.

## Address

- York, North Yorkshire — United Kingdom (full roastery street address not
  published on site; the registered address on the privacy policy is in
  Horsham and must not be confused with the York roastery).

## Sustainability

- Promotes ethical trade and rejects exploitation, with stated aims to keep
  improving its sustainability model and move toward a forward-contracting
  model for more stable producer income. No packaging or carbon
  certifications are claimed on the consulted pages.
- Wholesale customers in and around York get free local delivery via a "zero
  waste initiative" (standard local MOQ £60).

## Sourcing & Transparency

- Sources single origins through small, independent green-coffee
  partnerships with farm-level connections. Long-running partners include
  Omwani (East Africa), Coffee Cargo (Brazil), Karst Organics (East Timor),
  Yundian (China), Caribbean Goods (Guatemala), Micafe (Colombia), Forest
  Green Coffee (Colombia), Makicuna (Ecuador), Conscious (Peru/Bolivia) and
  Cofinet (Colombia/Peru microlots) — not every partner features in every
  current release.
- Defines traceability as knowing where, when and by whom a coffee was
  produced, and how it moved through the supply chain — noting that
  single-farmer tracing is not always financially viable for farmers who
  sell through collectives or washing stations.
- Specialty grade means coffee that officially scores above 80 points; about
  20% of coffees are spot-purchased and the rest pre-contracted, with an aim
  to expand into long-term forward contracts. The site says it pays above
  market rate but publishes no payment figures. Caribbean Goods' partner
  claims a farming technique that uses 90% less water (partner-specific).

## Roasting & Equipment

- Roasts on a Loring S15 "to maximise consistency, flavour quality and
  terroir expression" (per its subscriptions page); every batch is
  quality-checked at its QC lab in York.
- Light-sided roast style to preserve the green coffee's original character;
  roasts for both espresso and filter, and cups all samples blind before
  buying.
- No retail dark roast — though it supplies one specialty dark roast to
  Imperfect Coffee in Manchester (wholesale only).

## Schedules & Shipping

- Coffee is dispatched every Tuesday and Thursday (site header);
  subscriptions specifically are billed Mondays and dispatched Thursdays via
  a 48h service.
- Shipping policy: aims for UK delivery within five working days; £25+ order
  totals get free UK Standard delivery, orders under £25 pay £3 via Royal
  Mail Standard, and customers should get in touch after 10 days. The site
  header also claims free delivery over £20 — the detailed shipping policy
  (£25) is treated as current.
- Subscriptions rotate weekly, with weekly/fortnightly/monthly frequencies;
  free shipping is explicit for two-bag and 1 kg subscriptions, and they can
  be skipped or paused.

## Philosophy & Quirks

- The name comes from the "Harmonious Balance" category on the UK Barista
  Championship score-sheet (originally an inside joke); the Venn-diagram
  logo began as three overlapping circles for Ethics, Quality and
  Transparency, with Partnership added later.
- Ben Rowe has over a decade in specialty coffee, previously roasted at Kiss
  the Hippo in London, and has consulted on projects including the
  University of York. His competition record (attributable to Ben, not
  Harmony as a company): 11 open competition wins, 3rd in the SCA UK Latte
  Art Championship 2021, an SCA UK Barista Championship semi-final (Bristol
  heat winner Feb 2022 with 214.5), and narrowly missing England
  representation at the World Aeropress Championship 2024.
- Wholesale is the through-line: free local York delivery via the zero-waste
  initiative, unlimited free barista training for permanent/mainstay
  accounts, bespoke/guest/house coffees, custom packaging and white-label,
  equipment supply and maintenance, and public tastings/bar takeovers.
- The retail subscription launched in 2025; the roastery is not currently
  open to visitors.

## Scraping Quirks

- Shopify storefront scraped via products.json from the curated `our-coffee`
  collection; the root products feed additionally mixes in gift cards,
  subscriptions, equipment and merch — hence the scraper's explicit slug
  exclusions (subscription, gift-card, gift, wholesale, equipment, brewing,
  accessory, merchandise, apparel, mug, tumbler, hoodie, tshirt, capsules,
  pods, cold-brew-cans, easy-pour, felicita).
- Product URLs returned by products.json carry a
  `/collections/<handle>/products/<handle>` shape; the scraper strips the
  collection segment so catalogue URLs canonicalize to `/products/<handle>`.
- No tasting-kit products currently land in the coffee feed; if sampler or
  taster packs appear, they must be flagged `is_tasting_kit` /
  `requires_review` and flow through the review queue, never silently
  excluded.

## Sources

- https://www.harmonycoffee.co.uk/
- https://www.harmonycoffee.co.uk/pages/about-us
- https://www.harmonycoffee.co.uk/pages/faqs
- https://www.harmonycoffee.co.uk/pages/green-coffee-partners
- https://www.harmonycoffee.co.uk/pages/wholesale
- https://www.harmonycoffee.co.uk/policies/shipping-policy
- https://www.harmonycoffee.co.uk/collections/coffee-subscriptions
- https://www.harmonycoffee.co.uk/products/single-origin-subscription
- https://www.harmonycoffee.co.uk/collections/our-coffee