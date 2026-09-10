---
type: "Reference"
title: "Dear Green — Roaster Profile"
description: "Glasgow's B Corp roastery (est. 2011), named after the Gaelic for 'Dear Green Place' — Net Zero 2030 pledge, an in-house Q Grader, and a Decaf De Cana named Best Decaf by The Independent."
---

# Dear Green — Roaster Profile

## Overview

Dear Green began in Glasgow in 2011 — "just one woman, one trusty roaster" —
on a mission to bring specialty-grade coffee to Scotland. The name comes from
*Dear Green Place*, the Scots Gaelic for Glasgow. Now an award-winning B Corp
with a roastery, showroom and SCA-accredited training space in the city, it
roasts, supplies, educates and equips from one site. The storefront is Shopify
at [deargreencoffee.com](https://deargreencoffee.com).

## Address

- 101 Brook Street, Glasgow G40 3AP, Scotland, United Kingdom (roastery
  open 8:00–16:30 Monday to Friday; click & collect available the next
  business day after midday)

## Sustainability

- Certified B Corp since 2020 with a current score of **117.6**; pledged
  **Net Zero by 2030** with Scope 1–3 baseline measurement and a Carbon
  Trust-accredited offsetting programme (per their site).
- Roastery retrofit: solar panels, air-source heat pump, gas heating removed,
  double glazing; an EV fleet upgrade is in progress.
- Waste recycling with "nothing going to landfill"; coffee **chaff donated to
  local community gardening projects**.
- Partnered with AgriEvolve and Omwani to create a **coffee seedling nursery
  in Uganda**.
- Member of **1% for the Planet**, plus a further 1% of annual turnover
  committed to social justice organisations; 2% of "all we do" is donated to
  social and climate justice causes.

## Sourcing & Transparency

- Buys only through pre-approved, trusted importers on a "fully traceable
  route to the producer" — never from the commodity market; greens-grades and
  cups every lot on arrival.
- **Organic Food Federation certified since 2018** (annual audits); SALSA
  food-safety accredited; sources woman-produced and organic coffees whenever
  possible; in-house Q Grader licensed by the Coffee Quality Institute.
- Publishes an annual B Corp benefit corporation report and impact pages;
  a 2024 "In 2024, we bought:" sourcing summary appears in their impact
  reporting.

## Roasting & Equipment

- Roasts specialty-grade Arabica only, "roasted freshly, daily"; the roasting
  machine itself is not named on the site.
- In-house Q Grader (Coffee Quality Institute) and SCA-accredited training —
  the roastery doubles as a training space running SCA Sensory, Brewing and
  Green Coffee modules.

## Schedules & Shipping

- **Roasted daily.** Orders placed before 10:00 (Mon–Fri) are dispatched the
  same afternoon via Royal Mail 48 Tracked (allow up to 7 working days).
- **Free Royal Mail 48 Tracked shipping within the UK on orders over £30.**
- International orders via Royal Mail, up to 25 working days; EU orders under
  €150 have VAT and duties included at checkout. US shipping temporarily
  suspended due to tariff changes (per their site).

## Philosophy & Quirks

- Named after Glasgow's Gaelic nickname, the "Dear Green Place" — coffee
  "that comes from a good place".
- Community building is a stated mission: they founded the **Glasgow Coffee
  Festival in 2014**, kickstarted the UK Roasting Championships, and created
  Scotland's first women-in-coffee event.
- Their Decaf De Cana was named **Best Decaf by The Independent** (per their
  site); decaf is sourced and cupped with the same rigour as their
  single origins.
- Living Wage / Hours / Pension Foundation employer; Buy Women Built member.

## Scraping Quirks

- **Tasting kits flow to the review queue**: the `exclude_slugs` list has no
  bare `"kit"` entry, so products like the coffee-cupping-kit are extracted
  and flagged `is_tasting_kit`/`requires_review` rather than dropped.
- Dear Green renders a structured `ul.metafields-list` spec sheet (profile,
  harvest, process, variety, altitude, sourcing partner) only in the product
  page HTML's `div.description` — it is **not** in products.json, so the
  scraper's `preprocess_product_soup` reduces each product page to that
  description block for AI extraction.

## Sources

- https://www.deargreencoffee.com/
- https://www.deargreencoffee.com/pages/about-us
- https://www.deargreencoffee.com/pages/faqs
- https://www.deargreencoffee.com/pages/contact
- https://www.deargreencoffee.com/pages/environment
- https://www.deargreencoffee.com/pages/coffee-sourcing
