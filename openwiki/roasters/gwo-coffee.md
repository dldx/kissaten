---
type: "Reference"
title: "GWO Coffee — Roaster Profile"
description: "One-person micro-roastery from Eindhoven releasing light roasts as periodic themed drops, run from Kaffelogic → Roest L100 → Roest P3000."
---

# GWO Coffee — Roaster Profile

## Overview

GWO describes itself as a "Small specialty coffee roastery born in Eindhoven" with "an unreasonably passionate community", and states plainly that "GWO is still just me." The catalogue is not continuously stocked: coffee arrives as periodic themed drops ("For each drop I put together a set of coffees with a good mix of origins, processes, and flavour profiles"), with released coffees moving to a Past Releases archive. Style is explicitly light — "light roasts focusing on clarity, florals and acidity are worth exploring together" — with the aim of "letting the origin speak rather than the roast". Bag artwork comes from the owner's own paintings ("they're all rooted in my actual paintings"). The site is also candid that the store is empty on purpose: the roastery moved from a Roest L100 to a Roest P3000, and the first P3000 drop was scheduled for 25 October 2026.

## Address

- Eindhoven, Netherlands — a street address is not published on the contact or legal pages. The legal notice confirms the business as GWO Coffee, Netherlands, KvK 42032435, sole trader.

## Roasting & Equipment

- "First a Kaffelogic Nano 7, then a Roest L100, slamming out roasts in my kitchen and spare bedroom to now a Roest P3000 in a dedicated roasting space."
- The P3000 transition is why the store is currently empty; the same update also mentions improving the exhaust setup.

## Schedules & Shipping

- No fixed roasting day — fulfilment is drop-based, and roasting, QC, packing and shipping take "2 - 4 weeks of your order".
- Free-delivery thresholds, from the FAQ: Netherlands €4.95 shipping, free above €40; Germany, France, Belgium and Luxembourg €8.95, free above €70; rest of the EU €11.95, free above €100; rest of world a flat €15.95.
- Roast date is encoded in the batch code (example given: `L14Sep26-2`), and the site advises resting: "wait atleast 6 weeks after roast" with coffees at their best "in the 8-12 week period".

## Sourcing & Transparency

- "direct connections with the farms and suppliers behind the coffee" — the site claims direct connections but publishes no per-coffee price breakdowns or farm-gate figures.
- Explicit pricing philosophy: "the pricing should make sense."
- The P3000 was crowdfunded; the crowdfunding page states it was a one-time campaign and "Is this a subscription? No."

## Philosophy & Quirks

- Tasting sets are a real part of the range, themed rather than random: "I periodically pick three coffees based on a theme that I think fit nicely together as a set" (T.H.A.T. v3 / The Happy Accident Trio is 3×100 g).
- No founding year is published on the site.

## Scraping Quirks

- **The store is deliberately empty mid-transition.** As of writing, `current-collection` holds one placeholder product (`p3000-drops-loading`, "Big roaster drops loading...") that is priced at zero and unavailable, whose body explains the P3000 changeover, while the 14 real coffees sit in Past Releases and are all sold out. Expect long all-sold-out stretches and near-empty drops; a low product count is normal here and must not be treated as a broken scraper.
- Products are tagged `archive` once released and `product_type` is empty on everything, so neither field can be used to tell current from past stock.
- Bag size is shown as "100 g" even on products that ship as a 2×50 g set (e.g. GV Oma); read the body text rather than trusting the size field.

## Sources

- https://gwo.coffee
- https://gwo.coffee/pages/about-me
- https://gwo.coffee/pages/faq
- https://gwo.coffee/policies/shipping-policy
- https://gwo.coffee/policies/legal-notice
- https://gwo.coffee/collections/past-releases
- https://gwo.coffee/blogs/news/900-bags-later-gwo-update-7-30-09-2026