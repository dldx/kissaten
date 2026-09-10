---
type: "Reference"
title: "Rascal Coffee — Roaster Profile"
description: "Hackney roastery (est. 2020) built on six generations of Guatemalan coffee — every bean traces back to the family's Finca Filadelfia in Antigua, farming there since 1870."
---

# Rascal Coffee — Roaster Profile

## Overview

Rascal Coffee is a single-origin Guatemalan coffee roaster founded in 2020
(during the pandemic) by Alex Dalton and roasting in Hackney, East London.
The twist: the green coffee comes from **Alex's own family** — Finca
Filadelfia in Antigua, Guatemala, farmed by the family since 1870 across six
generations, plus a small number of other Guatemalan farmers (30+ Guatemalan
coffees to date). The storefront is Shopify at
[rascal.coffee](https://rascal.coffee).

## Address

- Hackney, East London — United Kingdom (roasted every Tuesday in East
  London; full street address not published on the site)

## Sourcing & Transparency

- Vertically integrated sourcing: coffee starts at **Finca Filadelfia**,
  Antigua — bought in 1870 by great-great-great-grandfather Manuel Matheu
  Sinibaldi, a pioneer of Guatemalan coffee known as the "grandfather of
  coffee", who travelled to London to sell his first crop.
- Alex's mother and sister run **Coffee Bird** in Guatemala, the sourcing
  operation that supplies Rascal's premium specialty lots — family at both
  ends of the chain.

## Schedules & Shipping

- Roasted **to order every Tuesday** and dispatched the same day (the
  shipping policy states orders are dispatched between 1–3 business days);
  most UK orders arrive within 1–3 days via Royal Mail Tracked 48.
- Free UK delivery over **£45**; Tracked 48 from **£4.26** otherwise.
- Subscriptions: 10% off every order, free shipping on 1 kg subscriptions,
  pause/skip/cancel anytime.

## Philosophy & Quirks

- Six generations deep: the story runs from Manuel Matheu Sinibaldi's 1870
  coffee loan in Antigua, through Alex's parents growing up on neighbouring
  coffee farms in El Salvador, to a pandemic-era roastery in Hackney.
- Hyper-focused range: Guatemalan single origins (Antigua, Huehuetenango,
  Acatenango), leaning on Antigua's volcanic soil, high altitude and shade
  growing — "la eterna primavera".

## Scraping Quirks

- **Label-image visual extraction**: no product page is fetched at all — the
  scraper builds context from Shopify `products.json` only and passes the
  product's **coffee label image** (filenames matching "label"/"etiqueta")
  to the AI extractor as a screenshot for visual analysis, falling back to
  the second product image.
- Product URLs are canonicalised by stripping the `/collections/coffee/`
  segment, matching the site's canonical `/products/<handle>` form.
- Non-coffee slugs (subscriptions, gift cards, equipment, apparel, capsules,
  cold-brew cans, easy-pours, …) are excluded before extraction.

## Sources

- https://rascal.coffee/
- https://rascal.coffee/pages/our-story
- https://rascal.coffee/pages/contact-us
- https://rascal.coffee/policies/shipping-policy