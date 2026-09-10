---
type: "Reference"
title: "Old Spike — Roaster Profile"
description: "London social-enterprise roaster since 2014 — named after workhouse slang, with 65% of profits funding barista training and paid placements for people affected by homelessness."
---

# Old Spike — Roaster Profile

## Overview

Old Spike (Old Spike Roastery) is a South London speciality roaster and the
UK's first social-enterprise speciality coffee roaster (per their site).
It was founded by two childhood friends who opened a small café in Peckham
in 2015 (their original story page dates the company to 2014), and has grown
to roasting in South London, seven London cafés (Peckham Rye, Southwark,
Sherwood St, Fenchurch St, Elephant & Castle, Canary Wharf …) and wholesale
across the country. Shopify storefront at
[oldspikeroastery.com](https://oldspikeroastery.com).

## Address

- 7 Gastineau Yard, Units 1 and 3a, LJ Works, London SW9 7FA — United
  Kingdom (roastery; coffee can be collected there)

## Sourcing & Transparency

- Sourcing is based on direct trade, quality and seasonality, working with a
  handful of UK speciality importers "committed to the same goals and values"
  (per their site).
- No FOB / farm-gate price figures are published — the position stated is
  that higher-quality coffee "means a better price for the farmer".

## Roasting & Equipment

- All coffee is roasted in South London; no specific roasting machine is
  named on the site.

## Schedules & Shipping

- Free Royal Mail 48 Tracked delivery when you spend £28; standard shipping
  rate £2.95.
- Under £28: Royal Mail 1st or 2nd class, or DPD Tracked Next Working Day
  (order by 8am for next-day delivery; weekend orders are processed on a
  Monday).
- No roast-day schedule is published.

## Philosophy & Quirks

- A "spike" was slang for a workhouse casual ward — the name references the
  Peckham workhouse near their first café (and George Orwell's 1931 essay
  *The Spike*); the point is the opposite of the workhouse: "training, paid
  work and a second chance to build a lasting career."
- Set up as a community interest company; **65% of profits** fund their
  Employment Programme for people affected by homelessness (per their site).
- The Employment Programme runs referral → Taster Days → a three-day
  Training Academy in Brixton → three weeks of paid work placement at the
  London Living Wage → support into lasting employment, with 20+ partner
  organisations (St Giles, Centrepoint, Baytree, Springboard …).
- Publishes outcome figures — for Jan–Jun 2026: 52 people trained, 92%
  completing a paid placement, 901 hours of paid employment, £13,355 paid
  in London Living Wage employment.
- Signature limited release: an Excelsa microlot from Nzara, South Sudan
  (honey anaerobic) — a rare, ~25%-less-caffeine species spotlighted as
  "Limited release 01".
- "Roaster's Choice" subscription: head roaster picks a different
  single-origin each delivery.

## Scraping Quirks

- The scraper reads a single quirky collection
  (`old-spike-roastery-200g-coffee-bags`) and canonicalises every collection
  URL to `/products/<handle>` because the same beans appear across several
  overlapping collections (`coffee`, `wholebean-coffees`, `espresso`,
  `filter-coffee`) — without canonicalisation, products would be scraped
  twice.
- The "benedict-blend" **subscription** product cannot be excluded by slug
  (its handle is a substring of the real bean `benedict-blend-espresso`), so
  it is dropped by the base class's title filter ("subscription" in title)
  instead.
- Non-coffee slugs excluded locally: `4kgs` bulk quantity SKU,
  `coffee-explorer-bundle`, `reusable-coffee-tin`, `roasters-choice`
  (subscription), plus defensive equipment/merch slugs.

## Sources

- https://oldspikeroastery.com/
- https://oldspikeroastery.com/pages/our-story
- https://oldspikeroastery.com/pages/our-story-new
- https://oldspikeroastery.com/pages/impact
- https://oldspikeroastery.com/policies/shipping-policy
- https://oldspikeroastery.com/pages/wholesale