---
type: "Reference"
title: "Intermission Coffee — Roaster Profile"
description: "West Hampstead, London coffeeshop-roaster on a hand-built WooCommerce shop — time-and-music-themed coffees (Power Hour, Jam Session, Tea Time), per-product green-buyer transparency and a weekly Monday-deadline dispatch rhythm."
---

# Intermission Coffee — Roaster Profile

## Overview

Intermission Coffee is a "coffeeshop in business to change the rhythm of the
world" in West Hampstead, London, with the stated mission to "put people and
planet first... and change the coffee industry for good." Unlike most roasters
in the catalogue, its main website is a hand-built one-page site (illustrated
with an animated clock and "Time for..." musings) while the web shop is a
WooCommerce store at `intermission.coffee/shop`. Wholesale runs on a separate
[orderspace](https://intermissioncoffee.orderspace.com/) portal.

## Address

- Unit 2, Hardy Building, West Hampstead, London NW6 2BR — United Kingdom
  (their only published location; the coffeeshop is just outside West
  Hampstead Overground station, and the product pages' "we roast Tuesday to
  Thursday" indicate roasting/dispatch happens from this site)

## Sourcing & Transparency

- Every product page names its **green buyer**: Caravela (El Salvador), Falcon
  (Kenya), Mi Cafe (Colombia), and producers/farmers are named alongside
  varietal, process and altitude.
- Mission statement emphasises that "everybody along our coffee supply chain is
  treated and paid fairly for their time" and working "with suppliers who share
  our values" (per their site — no FOB or farm-gate figures published).

## Schedules & Shipping

- Per product pages (cadence differs by product): "We roast Tuesday to
  Thursday. Orders are shipped every Thursday. Orders must be placed by
  midnight on Monday for same week dispatch. We ship via Royal Mail first
  class." Filter coffees list "We roast Monday & Tuesday. Orders are shipped
  every Wednesday... Royal Mail tracked 48."
- No free-delivery minimum is published.

## Philosophy & Quirks

- The whole brand plays on time and music: coffees are named **Power Hour**,
  **Jam Session**, **Tea Time**, **The Midnight Train**, **Working 9 to 5**,
  **Sundial**, **Circadian Rhythm**, **Just a Minute**, **Around the World in
  80 Days** and **The Domino Effect** (named after the German sweet, not the
  game).
- The homepage is a poetic "Time for a break / Time for a mindless scroll /
  Time to google baby pigeons..." scroll ending in "Time for coffee", with a
  clock graphic ticking through "Years to grow / Weeks to process / Months to
  ship / Hours to roast / Minutes to make / Moments to drink."
- The site credits its design to Fieldwork Facility, build to Karol Kalna and
  illustrations to Tomi Um.
- Founding year is not published on the site.

## Scraping Quirks

- **The shop really sells a product called "Test Roast"** — the scraper's
  exclusion list (`test-roast`, `subscription`, `gift-card`, `wholesale`,
  `equipment`, …) is not hypothetical: it is needed to keep the live "Test
  Roast" product out of the catalogue.
- The scraper pulls the whole `/shop/product-category/everything/` archive and
  filters locally; several sibling categories (Equipment, Guest Coffee,
  Intermission Merch) are empty archives.
- Wholesale lives on a separate `intermissioncoffee.orderspace.com` storefront
  that is not scraped — don't confuse it with the WooCommerce shop.

## Sources

- https://www.intermission.coffee/
- https://www.intermission.coffee/shop/
- https://www.intermission.coffee/shop/product/power-hour/
- https://www.intermission.coffee/shop/product/around-the-world-in-80-days/
- https://www.intermission.coffee/shop/product/the-domino-effect-advanced-natural-gesha-colombia/
- https://intermissioncoffee.orderspace.com/
