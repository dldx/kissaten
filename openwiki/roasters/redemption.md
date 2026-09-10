---
type: "Reference"
title: "Redemption Roasters — Roaster Profile"
description: "London social enterprise roasting inside a working prison — a Loring roaster at HMP The Mount, barista academies that cut reoffending to 4%, and house coffees named The Yard and The Block that rotate by edition."
---

# Redemption Roasters — Roaster Profile

## Overview

Redemption Roasters is a London social enterprise founded in October 2016, when
co-founders Ted and Max — previously of wholesale company Catimor Ltd — were
approached by the Ministry of Justice about setting up a roastery in a prison to
train residents and reduce reoffending. It runs **eleven coffee shops across
London** (the first opened on Lamb's Conduit Street in Bloomsbury in 2017) on a
Shopify storefront at [redemptionroasters.com](https://redemptionroasters.com),
and has been awarded the King's Award for Enterprise (per their site). House
coffees have prison-flavoured names — The Yard, The Block, The Governor, The
Roll Call.

## Address

- Roastery inside **HMP The Mount**, Bovingdon, near Hemel Hempstead,
  Hertfordshire — United Kingdom (a working prison; street address not
  published on the site)

## Sustainability

- The whole business is a rehabilitation programme: barista academies run in
  prisons (historically HMYOI Aylesbury, now HMP Pentonville and High Down,
  plus a community academy for prison leavers), with graduates employed in
  their London shops — 20% of hospitality staff were "Participants" as of the
  end of 2023.
- At the close of 2023, employed Participants' reoffending rate was **4%**
  versus a 42% national average (per their site). A fee is paid to HMP The
  Mount for operations, part of which compensates residents for their work,
  plus a bonus paid in full on release.
- Publishes an annual Social Impact Report (2025 edition on the blog).

## Sourcing & Transparency

- Dedicated cost-breakdown pages on the site: green price, production costs,
  transport costs, redemption costs, lot size and C-market commentary —
  green coffee is bought via farm-gate, FOB, EXW and spot purchasing.
- **89% of coffee contracted in 2025** met at least one of their social
  sourcing goals (per their site):
  - **Rehabilitation (12%)** — a Colombian project supporting farmers leaving
    paramilitary involvement and illicit crops.
  - **Sustainable initiatives (52%)** — via importers Caravela (upfront
    payment plus on-the-ground agronomy) and Raw Material CIC (reinvests all
    profits at origin).
  - **Female economic empowerment (31%)** — including Patricia Coelho (Brazil),
    whose coffee anchors house espresso The Block.

## Roasting & Equipment

- A **Loring roaster** installed at HMP The Mount in March 2020, producing
  several tonnes of roasted coffee per month (the original roaster installed
  at HMYOI Aylesbury in 2017 was moved rather than replaced).

## Schedules & Shipping

- Roasted at HMP The Mount and dispatched **Monday to Friday**, next working
  day after purchase, via Royal Mail.
- Under £25: Royal Mail Tracked 48 £3.95 (3–5 working days); Tracked 24 £4.95
  (1–3 working days).
- **Over £25: Tracked 48 free**; subscriptions always ship Tracked 48 free.
- The site candidly warns of delivery delays — "operating a roastery behind
  bars… no two days look the same".

## Philosophy & Quirks

- Tagline: "We train prison leavers with the skills they need to gain secure
  and meaningful employment."
- Several house coffees keep stable product slugs while the bean inside
  **rotates seasonally** — The Yard is a seasonally re-blended espresso whose
  origins and tasting notes change each edition.

## Scraping Quirks

- **Rotating editions need fresh URL identities**: stable slugs like `the-yard`
  hide rotating beans, so the scraper appends the first product image's CDN
  `?v=` version as a URL fragment (`products/<handle>#<version>`). A rotation
  changes the image version, producing a new URL that is scraped fresh while
  the old one is marked out-of-stock by the diffjson flow — preserving
  history instead of overwriting. Only the FIRST image is used (one URL per
  product), since Redemption's extra images are marketing shots of the same
  bean.
- **Overlapping collections canonicalised**: product URLs from collection
  endpoints are stripped to `/products/<handle>` so a product found in
  multiple collections is never scraped twice.
- Coffee-pod SKUs (everyday/dark-roast/light-roast/taster-pack pods) are
  caught by the `pods` exclude slug rather than being kit-flagged.

## Sources

- https://redemptionroasters.com/
- https://redemptionroasters.com/pages/about-us
- https://redemptionroasters.com/pages/roastery
- https://redemptionroasters.com/pages/delivery-and-returns
- https://redemptionroasters.com/pages/faqs
- https://redemptionroasters.com/pages/green-price
