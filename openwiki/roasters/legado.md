---
type: "Reference"
title: "Legado — Roaster Profile"
description: "Stellenbosch (Cape Winelands) roaster built around one of South Africa's original Diedrich roasters, with a light, nuanced roast style and free nationwide shipping."
---

# Legado — Roaster Profile

## Overview

Legado Coffee Roasters (legado means "legacy" in Portuguese) was founded in
2010 by three friends with a vision of "good business and exceptional coffee".
The company took shape around a piece of South African coffee history: one of
the country's original Diedrich roasters, acquired from its long-time owner
together with his mentorship. From that base Legado grew into roasting for its
own retail line as well as contract roasting, and describes itself as leaving
"a legacy of quality & equality". The Shopify storefront sells single origins
(Brazil, Colombia, Ethiopia, Guatemala, Rwanda) and two blends (The Espresso
Blend, The Journeyman Blend).

## Address

- Shop 5, The Woodmill Lifestyle Centre, Stellenbosch, 7600, South Africa

## Roasting & Equipment

- Roasts on one of South Africa's original Diedrich drum roasters, acquired
  with the guidance of its previous owner (per their what-we-do page).
- Deliberately light, nuanced roast style intended to let origin
  characteristics shine (per their site).

## Schedules & Shipping

- "Fast Free Shipping — we ship nationwide, free of charge" (no minimum
  order value published).

## Philosophy & Quirks

- The name and brand story centre on legacy: honouring the machine, mentor
  and craft that founded the company.
- The broader `all` collection mixes the coffee line with catered morning and
  evening event packages (venue-only and canapés/drinks formats) rather than
  equipment or merch.

## Scraping Quirks

- The curated `coffee-beans` collection ("Freshly Roasted Coffee") holds the
  whole retail bean line-up; the scraper uses it instead of `all`, which adds
  the event-catering packages. A defensive `exclude_slugs` net
  (`event`, `catered`, `venue`, …) guards against those leaking in.
- Store currency is pinned to ZAR with `Accept-Language` removed so Shopify
  Markets geo-conversion cannot re-stamp prices for a datacenter IP.
- Extraction is JSON-only: the products.json `body_html` already carries
  variety, altitude, processing method and tasting notes.

## Sources

- https://legadocoffee.com
- https://legadocoffee.com/pages/what-we-do
- https://legadocoffee.com/pages/wholesale
- https://legadocoffee.com/collections/coffee-beans
