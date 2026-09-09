---
type: "Reference"
title: "Father Coffee — Roaster Profile"
description: "Johannesburg roaster of 'very good coffee since 2013', running a Kramerville roastery-café-bakery-winebar complex and a deep bench of African and Latin American microlots and Rare Release® lots."
---

# Father Coffee — Roaster Profile

## Overview

Father Coffee ("Roasters of Very Good Coffee since 2013") is a specialty
coffee roastery in Johannesburg, South Africa that seeks out coffees that are
"exemplars of provenance, varietal and processing". The Shopify storefront
sells an unusually deep single-origin bench — Microlot and Special Release
lines plus a top-tier Rare Release® series (e.g. Chombi Natural Geisha by the
Altieri Family, Zeo Geisha by El Paraíso) — alongside blends such as Coffee
Coffee ("tastes like coffee") and Heirloom Blend. The Kramerville site
combines roastery, café, kitchen, bakery, wine bar, shop, training rooms and
a cupping lab; there is a second café in Rosebank, plus a Father Coffee
Factory shop and a green-coffee shop. Sold-out and past lots are kept visible
in "The Archives" collection.

## Address

- 19 Dartfield Road, Kramerville, Johannesburg, South Africa (roastery,
  café, kitchen, bakery, wine bar & shop, training rooms & cupping lab)

## Schedules & Shipping

- All online orders are typically shipped on Wednesdays to ensure the
  freshest stock; anything ordered by midnight Tuesday is guaranteed to ship
  that Wednesday, later orders ship by the following Wednesday at the latest.
- Free South African delivery on orders over R899; below that a R89 delivery
  fee applies at checkout. Johannesburg orders often arrive the day after
  tracking, other major centres ~2 days, outlying areas up to 3 days.
- International shipping on orders under 2kg via Aramex or DHL ("a little
  steep" per their shipping FAQs, but tracked end-to-end).
- Store pickup is offered from the Kramerville Roastery or the Rosebank Café.

## Philosophy & Quirks

- Tongue-in-cheek brand voice throughout (the contact page is "Hello there"
  and offers an "emergency hotline … if you have nothing left in your
  cupboard but instant coffee").
- Also sells natural wine and pantry goods ("Hot Sauce" / "Not Hot Sauce")
  from the same complex.
- SuperSub® is their coffee subscription format, with its own catalogue pages.

## Scraping Quirks

- Not to be confused with the Czech roaster "Fathers" (`fathers.py`), which
  already existed in the registry — this scraper is `father-coffee` for the
  Johannesburg roastery.
- The curated `coffee` collection holds the bean line-up; the one non-bean
  entry in it (Seasonal Capsules) is dropped via the `capsules` exclude slug.
- Bean detail (producer, region, variety, altitude, process, cupping and brew
  notes) lives behind a "Product Details" collapsible tab rendered as Shopify
  metafields on the product page, not in the collection `body_html` — the
  scraper prunes the page soup to the description + collapsible-tab blocks
  before AI extraction.
- Shopify handles can drift from titles (e.g. `ethiopia-chelbesa-red-honey`
  is titled "Rwanda - Vunga - Natural", and a `…-copy` handle carries a
  different coffee's name) — trust titles/page content, not handles.
- Store currency is pinned to ZAR with `Accept-Language` removed so Shopify
  Markets geo-conversion cannot re-stamp prices for a datacenter IP.

## Sources

- https://www.father.coffee
- https://www.father.coffee/pages/hello-there
- https://www.father.coffee/pages/shipping-guide
- https://www.father.coffee/collections/coffee
- https://www.father.coffee/products/karimikui-aa
