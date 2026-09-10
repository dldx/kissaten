---
type: "Reference"
title: "Rave Coffee — Roaster Profile"
description: "Cirencester roastery (UK, est. 2011 in a converted shed) with twin Loring roasters, roast-to-order same-day despatch, and a 1% for the Planet conscience — 25k+ trees planted."
---

# Rave Coffee — Roaster Profile

## Overview

RAVE Coffee is a speciality roaster in Cirencester, Gloucestershire, started
in the UK on 1 January 2011 by Rob and Vikki Hodge — literally in the back of
an old converted shed in nearby Avening — after time in Australia. Within
seven months they moved to Love Lane, Cirencester, and in spring 2023 into a
renovated former derelict building on Phoenix Way that now houses the
roastery and an attached HQ café/shop. The Shopify storefront at
[ravecoffee.co.uk](https://ravecoffee.co.uk) sells blends, single origins,
rare micro-lots, organic coffee, decaf, compostable Nespresso-compatible
pods, cold brew, syrups and even coffee liqueur, with 24k+ five-star reviews
and a subscription *The Independent* named Best Overall Coffee Subscription
in 2024.

## Address

- Rave Coffee HQ, Phoenix Way, Cirencester, Gloucestershire, GL7 1QG —
  United Kingdom (roastery + HQ café/shop; registered office Southgate
  House, Phoenix Way)

## Sustainability

- **1% for the Planet member** — 1% of all sales donated to environmental
  causes regardless of profitability; site counters report 25,507 trees
  planted and tens of thousands of pounds donated.
- **One Tree Planted** partnership — 25,507+ trees planted to date.
- **Project Waterfall** — clean water, sanitation and education for
  coffee-growing communities.
- **Fauna & Flora International** — wildlife conservation support.
- **Tusk African Blend**: a charity coffee with £1 from every bag going to
  Tusk's African conservation efforts.
- Runs on sustainable green electricity; sells compostable Nespresso-style
  pods.

## Sourcing & Transparency

- Minimum quality bar published on the about page: coffee scoring **82+ SCA
  points for blends** and **84+ for single origins** as a starting point.
- Explicit pricing philosophy: "the coffee is what you should pay for, not
  the box it might come in" — deliberately plain packaging to keep prices
  down.

## Roasting & Equipment

- Two **Loring** roasters at the Phoenix Way HQ — a 70 kg and the original
  35 kg — installed around the spring 2023 roastery move.
- Roast to order, five days a week (Saturdays in busy periods).

## Schedules & Shipping

- Orders are checked every morning **Monday–Friday at 6:00 am**; the daily
  roast schedule is built from them and orders placed before the cutoff are
  roasted and despatched **the same day**. Orders after Friday 6:00 am roll
  to Monday.
- Free UK tracked delivery over **£25**.
- International shipping was "currently suspended due to delays outside of
  our control" per their roasting page.

## Philosophy & Quirks

- Self-deprecating about-page voice: "At this point we could rave on about
  company pedigree and vision for the future (blah blah yawn) but that's
  simply not our way."
- "We serve great coffee, not moral judgment" — decaf, pods and syrups sit
  happily next to rare micro-lots.
- Numbered blends: Signature Blend Nº 1, The Italian Job Blend Nº 2,
  Fudge Blend Nº 5, Swiss Water Decaf Blend Nº 11.
- Proud of staff and community: "happy passionate staff in a fun working
  environment equals satisfied customers", with the HQ café as "our own
  little coffee community".

## Scraping Quirks

- **Overlapping collections deduped by URL canonicalisation**: the scraper
  pulls four collection `products.json` feeds (roasted-coffee,
  single-origin-coffee, coffee-blends, decaf-coffee-beans) and strips the
  `/collections/<slug>` segment from every URL, so beans listed in several
  collections merge onto a single canonical `/products/<handle>` URL instead
  of being scraped twice.
- Non-coffee products (pods, bundles, coffee liqueur, capsules, compostable
  bags, zip-lock bags) are excluded by **substring match** against the
  handle — the exclusion list was verified so that no real bean handle
  contains those slugs (a caveat: short generic slugs like "pod" or "bag"
  would risk dropping genuine beans).

## Sources

- https://ravecoffee.co.uk/
- https://ravecoffee.co.uk/pages/about
- https://ravecoffee.co.uk/pages/roasting
- https://ravecoffee.co.uk/pages/1-for-the-planet
- https://ravecoffee.co.uk/pages/contact-us
- https://ravecoffee.co.uk/blogs/news/raves-new-hq
- https://ravecoffee.co.uk/blogs/news/vikkis-blog-building-rave-hq-part-1