---
type: "Reference"
title: "Yunara Coffee — Roaster Profile"
description: "Swansea (Wales) micro-roastery sourcing and roasting small-batch single origins and blends — Liberica Purple Honey, washed Gesha, Caturra decaf — on Shopify; the checklist's 'Yunnara' is a common misspelling."
---

# Yunara Coffee — Roaster Profile

## Overview

Yunara Coffee (yunara.coffee) is a micro-roastery based in Swansea, Wales,
with a registered office in Mumbles. The name is a reminder "to work carefully
and take our time" (per their about page). It roasts and sources small-batch
coffees on a Shopify storefront; the curated coffee collection holds 8
whole-bean coffees — Guayaba (Colombia), Ñuu Davii (Mexico), JB Coffee Liberica
Purple Honey (Indonesia), Gitwe Hill (Burundi), Gundikhan Estate (India),
Bolney Reinoso washed Gesha (Colombia), Ivan Sebay pink bourbon (Colombia) and
Los Nogales Caturra decaf (Colombia) — plus espresso/filter subscriptions and
workshops.

## Address

- Micro-roastery in Swansea, Wales — full street address not published on
  site (registered office in Mumbles, Swansea). United Kingdom.

## Sourcing & Transparency

- The per-bean catalogue detail (origin country/region, producer, process,
  variety and tasting notes) is published in the store, spanning rare lots such
  as Indonesian Liberica Purple Honey, a washed Gesha and a pink bourbon.

## Scraping Quirks

- The checklist entry "Yunnara" is a misspelling of Yunara: the correct display
  name is Yunara Coffee at yunara.coffee (row corrected in
  `uk_roasters_checklist.md`).
- Espresso/filter subscriptions and workshops/events are sold outside the
  curated coffee collection and are excluded; tasting-kit/sampler tokens are
  deliberately not excluded so kits flow to the review queue.
- The edge rejects curl_cffi's default libcurl TLS fingerprint (403 on
  products.json) — the scraper rebuilds its client with `impersonate="chrome"`
  (mirrors twoday.py).

## Sources

- https://yunara.coffee
- https://yunara.coffee/pages/about
- https://yunara.coffee/pages/contact