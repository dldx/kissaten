---
type: "Reference"
title: "MUYU Coffee Roasters — Roaster Profile"
description: "Locarno micro-roastery bridging Switzerland and Bolivia through solar-powered roasting, direct farm-gate pricing and Proyecto Elevate."
---

# MUYU Coffee Roasters — Roaster Profile

## Overview

MUYU Coffee Roasters is a family-run micro-roastery in Locarno, Switzerland,
founded by Vanessa and Yann after three years helping establish sister roastery
Elevate Coffee in Bolivia. The Squarespace storefront focuses on Bolivian
espresso and filter coffees, with accessories and education alongside the bean
shop. MUYU describes its work as a bridge between Switzerland and Bolivia.

## Address

- Via Castelrotto 18A, 6600 Locarno, Switzerland.

## Sustainability

- MUYU says its complete shop operation runs on locally generated solar power
  purchased through the certified TiSole programme, including its electric
  roaster, espresso machine and grinders.
- Domestic Swiss shipments are sent carbon-neutral through Swiss Post’s
  “Pro Clima” label, according to the shipping page.

## Sourcing & Transparency

- Through Proyecto Elevate, MUYU and Elevate Coffee source exclusively from
  small, family-run Bolivian fincas, including farms that usually lack access
  to international markets.
- The site says it publishes the farm-gate price paid for each bean in the
  online shop, pays directly and immediately, and supplements purchasing with
  producer knowledge input, project-specific microfinancing and feedback. No
  concrete per-coffee price figures were captured on the reviewed pages.

## Schedules & Shipping

- Coffee is freshly roasted on demand and shipped the same day as the order.
  Free shipping is advertised for orders over CHF 120.
- Swiss Post delivery is described as next-working-day Priority or 2–3 working
  days Economy in Switzerland; international orders are tracked and usually
  take 4–10 days. Published destinations include Switzerland, Liechtenstein,
  selected European countries (Iceland, Norway and the UK), and Australia,
  Canada, Japan, New Zealand, Singapore, South Korea and Taiwan. Duties and
  VAT outside Switzerland and Liechtenstein are charged to the recipient.

## Philosophy & Quirks

- The founders describe MUYU as a “love story between Switzerland and Bolivia”
  and the business as a way to redesign the supply chain around smallholder
  resilience and environmental compatibility.

## Scraping Quirks

- The custom storefront exposes coffee in separate `/shop/espresso` and
  `/shop/filter` pages. Product cards use `div.product-list-item`; the scraper
  drops cards carrying the exact `sold-out` class before filtering, excludes
  subscriptions, gifts, courses, merchandise and equipment, and forces the
  extracted currency to CHF.

## Sources

- https://muyu.coffee/about
- https://muyu.coffee/shipping-returns
- https://muyu.coffee/shop
