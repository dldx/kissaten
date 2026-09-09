---
type: "Reference"
title: "Rosetta Roastery — Roaster Profile"
description: "Cape Town specialty roaster (est. 2010) with four coffee bars around the city, a Claremont roastery, Progressive/Classic roast styles and a single-origin-led range priced in ZAR."
---

# Rosetta Roastery — Roaster Profile

## Overview

Rosetta Roastery is a specialty coffee roaster founded in Cape Town, South
Africa in 2010 by Jono Le Feuvre, Rob Cowles and Jeff van Aswegen, with Ian
"The Uncle" Scott later joining as co-owner. The range is single-origin-led —
rotating lots from Peru, Colombia, Brazil, Ethiopia, Kenya, Rwanda and
Indonesia, plus a decaf and drip sachet boxes — with each coffee tagged
"Progressive" (lighter, filter-oriented) or "Classic" (fuller, espresso- and
milk-oriented). The tagline "Join the Pursuit Toward Coffee Perfection" runs
across the site. Beyond the Shopify store, Rosetta operates four coffee bars
(Bree Street, Claremont, BlackBrick Gardens and a Silo District pop-up).

## Address

- Ground Floor, 1 Osborne Road, Claremont, Cape Town, South Africa — the
  roastery sits next door to the Claremont café and is described as a
  production space where visitors can watch the roasting team at work.

## Sourcing & Transparency

- Their sourcing-philosophy page commits to paying above the commodity "C"
  price so producers can earn more than production costs, re-invest and
  sustain a fair lifestyle, working with "a select group of green coffee
  wholesalers who share a similar focus".
- Per-product pages name the producer, farm, region, importer/partner (e.g.
  La Chirimoya sourced through Origin Coffee Lab) and certification (e.g.
  certified-organic lots), though no FOB/farm-gate figures are published.

## Roasting & Equipment

- Coffees are classified into two roast styles: "Progressive" (lighter body,
  flavour-nuance forward, for filter) and "Classic" (fuller body,
  roast-centric but still "very moderate medium roasts", for espresso and
  french press). No roasting hardware is published on site.

## Schedules & Shipping

- Free delivery on all orders over R650 (ZAR).
- Collection (free) at the Bree St café, ready by the Tuesday or Friday after
  ordering.
- Greater Cape Town: R65, dispatched Tuesdays and Fridays, same-day or
  next-day arrival.
- Rest of South Africa: R95, courier 1–3 working days after dispatch.
- Subscriptions are dispatched on the first Friday of every month.

## Philosophy & Quirks

- "Coffees are orchids. Not aspirins" — their stated belief that coffee should
  be an infinitely varied, transient treat rather than a manufactured
  daily medicine.
- The founders' story is told with self-deprecating humour: the three
  founders shared a house and played in a nu-metal band (Citizen Kane) before
  turning to specialty coffee.
- The shop also carries a "Blind Tasting Box" catalogue and 10-pack drip
  sachet mix boxes alongside whole beans.

## Scraping Quirks

- The curated `collections/coffee` endpoint is the bean catalogue;
  `collections/all` also mixes in subscriptions, equipment and merch.
- The compostable coffee capsules product is caught by the `capsules`
  exclude-slug even though Shopify classifies it as product_type "coffee";
  drip sachet boxes and the multi-bag Signature Selection set are kept and
  flow through the tasting-kit review flags if the AI recognises them as kits.
- Product URLs are canonicalised to the no-collection `/products/<handle>`
  form the live site serves, and store currency is pinned to ZAR against
  Shopify Markets geo-conversion.

## Sources

- https://www.rosettaroastery.com
- https://www.rosettaroastery.com/pages/our-story
- https://www.rosettaroastery.com/pages/sourcing-philosophy
- https://www.rosettaroastery.com/pages/roast-styles
- https://www.rosettaroastery.com/pages/locations
- https://www.rosettaroastery.com/pages/faqs
- https://www.rosettaroastery.com/pages/delivery-terms-and-conditions
- https://www.rosettaroastery.com/pages/contact
- https://www.rosettaroastery.com/collections/coffee/products.json
