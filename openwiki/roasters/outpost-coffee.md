---
type: "Reference"
title: "Outpost Coffee — Roaster Profile"
description: "Small independent Nottingham roastery — hand-roasted batches (no automation), a Mon–Thu roast schedule, DPD carbon-neutral dispatch, and strong ties to La Marzocco."
---

# Outpost Coffee — Roaster Profile

## Overview

Outpost Coffee Roasters is "a small, independent & focused specialty coffee
roastery based in Nottingham, England" (per their site), built around the
motto "FIND. INCREDIBLE. COFFEE." They roast seasonal blends, single origins
and rare microlots in-house, with a taste for innovative processing
(anaerobic naturals and washed geshas feature prominently, e.g. Blue Ayarza
Guatemala anaerobic natural 120 hrs, Los Quispe anaerobic washed Gesha Peru).
Shopify storefront at [outpost.coffee](https://outpost.coffee); no founding
year is published on the site.

## Address

- 32 Salisbury Square, Nottingham, England NG7 2AB — United Kingdom

## Sourcing & Transparency

- Ethos (per their roast-schedule page): all coffees come from "exceptional
  growers … who deserve real praise and better pay", supporting sustainable
  supply chains that let growers "earn a consistent and good price".
- No FOB / farm-gate price figures are published.

## Roasting & Equipment

- Each batch is roasted carefully **by hand, "no automation"** (per their
  site), to showcase the coffee's best profile — "roasting is always
  conceptual".
- No roasting machine is named on the site.
- Beyond roasting, Outpost is a La Marzocco stockist (Linea Mini, GS3, Lux
  D) with an equipment servicing network, runs barista workshops, and sells
  Aoomi ceramics.

## Schedules & Shipping

- Roasts and dispatches **Monday–Thursday** via DPD's Tracked carbon-neutral
  service and Royal Mail 24.
- Orders received before 11am GMT (Mon–Fri) ship the same day; as coffee is
  roasted to order, occasional orders dispatch the next business day.
- Coffee roasted up to 7 days before the order date may be sent; specific
  roast dates can be requested.
- Free UK shipping over **£25** (DPD); UK orders under £25 are £4.95.
- International shipping is temporarily suspended ("due to the ongoing
  effects of Brexit and increased international trade tariffs").
- Rest advice: 5–7 days rest before opening, best within a month of roast.

## Philosophy & Quirks

- Wholesale-first mindset: free in-person barista training for partners,
  access to Barista Hustle online courses, equipment finance support, and
  own-blend/own-label options.
- "Roasting is always conceptual" — an unusually candid philosophy note on
  their roast-schedule page.
- Contactable on the phone at 0115 8374320, an unusual local Nottingham
  landline for a speciality roaster.

## Scraping Quirks

- The scraper walks the `/collections/coffees` HTML rather than
  `products.json` (plain `BaseScraper` + AI extraction, no Playwright), so
  any product not rendered as a `/products/` link in that collection is
  invisible to it.
- Outpost-specific exclusions beyond the usual subscription/equipment slugs:
  `test-roast` (a test product) and `lucky-dip` (a lucky-dip coffee bag), plus
  `fellow-` equipment — keep those out of the catalogue rather than flagging
  them.

## Sources

- https://outpost.coffee/
- https://outpost.coffee/pages/about-us
- https://outpost.coffee/pages/roast-schedule
- https://outpost.coffee/pages/why-partner-with-us
- https://outpost.coffee/policies/shipping-policy