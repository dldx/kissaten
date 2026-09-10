---
type: "Reference"
title: "Skinny Dip Coffee — Roaster Profile"
description: "Margate roastery built around championing women in coffee — roast days Mon/Thu/Fri, a Subbly one-page shop, and subscription tiers named Usual, Curious and Impossible."
---

# Skinny Dip Coffee — Roaster Profile

## Overview

Skinny Dip Coffee (trading as Skinny Dip Coffee Roasters) is a specialty roastery
in Margate, Kent, whose sourcing is deliberately built around **women in coffee**
— the site opens its producer section with the question "Would you do 70% of the
work for 20% of the money?" and cites 2018 International Coffee Organisation
research on women's lower access to land, credit and information. The storefront
is a **Subbly** one-page shop (buy-coffee page with per-product anchors). The
roastery also doubles as a brew bar, open to the public weekdays and Saturdays.
A separate Skinny Dip café operates in Cliftonville (Northdown Road), opened in
winter 2020 — per press coverage, not the roastery site.

## Address

- Skinny Dip Coffee Roasters, Unit J1H, Channel Road, Westwood Industrial
  Estate, Margate, Kent CT9 4JS — United Kingdom (the contact page writes the
  postcode "CT9 4SJ"; the homepage says CT9 4JS)

## Sourcing & Transparency

- All coffees are positioned as sourced from **female-led producers and
  women's groups**: e.g. Kajere Women's Mountain (Uganda), Ikezere Women's
  Group (Rwanda, via Fugi washing station & Baho Trading Company) and Rama
  Women's Association (Burundi), alongside named-farm Colombia and Guatemala
  lots.
- Wholesale includes barista training and setup advice alongside the seasonal
  coffee menu.

## Schedules & Shipping

- Roasting happens on **Mondays, Thursdays and Fridays**; orders are asked for
  by **midnight the day before** a roast day (stated on the wholesale page, "at
  the moment the bulk of our roasting is done on a Monday, Thursday and
  Friday").
- No free-delivery minimum or per-region rates are published on the site.

## Philosophy & Quirks

- The roastery is also a drop-in brew bar: "Come and have a brew with us in
  the roastery", open 8:30am–2pm Mon–Fri and 9am–1pm Saturday.
- Subscription tiers are named **Usual**, **Curious** and **Impossible**
  (headlined on the shop page as "Daily Grind", "Adventurous", "Something
  Special").
- Playful product naming and tasting notes: house blend **Birthday Suit**
  ("Black Forest Gateaux"), and notes like "Chocolate Milkshake, Cherry
  Bakewell & Strawberry Quality Streets".
- Per press (Kent Live), Skinny Dip was named the UK's "most innovative" coffee
  house at BRITA Professional's inaugural Grounds of Innovation Awards for its
  championing of women in the trade.

## Scraping Quirks

- **Subbly one-page shop with no per-product URLs**: every product lives on
  the same `/buy-coffee` page, so the scraper synthesises unique URLs as
  anchors (`/buy-coffee#<slug>`) from the raw product title.
- Product rows are anchored on `.module.ModuleTitle` blocks and walked up to
  the enclosing `uc-row-wrapper`; titles are usually `<h3>` but some products
  use `<p><strong>` instead.
- Non-coffee rows are excluded **by name** — the subscription tiles
  ("Usual", "Curious", "Impossible") and the "Visit Us" block would otherwise
  be picked up as products.
- Rows containing "Coming Soon" or "Out of Stock" are skipped (upcoming
  releases like "El Encanto" are filtered out), with word boundaries so
  "incoming soon" copy in accordions doesn't false-match; the `test-roast`
  slug is also excluded.

## Sources

- https://www.skinnydipcoffee.co.uk/
- https://www.skinnydipcoffee.co.uk/contact-us
- https://www.skinnydipcoffee.co.uk/buy-coffee
- https://broadstairsfoodfestival.org.uk/event/skinnydipcoffeeroasters/ (co-founder names)
- https://www.kentlive.news/whats-on/food-drink/award-winning-margate-coffee-shop-8974293 (award)