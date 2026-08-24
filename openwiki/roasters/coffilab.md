---
type: "Reference"
title: "Coffi Lab — Roaster Profile"
description: "Cardiff (Wales) speciality coffee roaster on Shopify with a dog-lover identity — every coffee is a 'Lab' (Fox Red, Black Lab, Silver Lab…), roasted small-batch on a Giesen, with Great Taste awards, sampler boxes and a 'Pawsonalise a Coffee' gift service."
---

# Coffi Lab — Roaster Profile

## Overview

Coffi Lab is a Cardiff (Wales) speciality coffee roaster on a Shopify storefront
at coffilab.co.uk, built around a dog-lover identity: every coffee
is a "Lab" (Fox Red, Yellow Lab, Black Lab, Choc Lab, Silver Lab, Golden Decaf,
…), several carrying Great Taste awards, roasted in Cardiff. The
curated coffee collection holds 16 products, including the Fox Red signature
roast, sampler boxes (The Lab Pack, Lab Duo pairs) and a "Pawsonalise a
Coffee" personalised-label gift service on the same core coffees. It also runs
a chain of neighbourhood "Labs" (cafés) across South Wales and the South West and supports Guide Dogs UK.

## Address

- The Coffi Lab, 55 Penlline Road, Cardiff CF14 2AB — United Kingdom

## Roasting & Equipment

- Small-batch roasted in Cardiff on a Giesen named in tribute to the founder's Labrador Dylan (per their site).

## Schedules & Shipping

- Free UK delivery over £30 (Royal Mail 48hr), free 48hr tracked delivery on
  subscriptions, £3.50 otherwise; dispatch within 2 working days, with orders
  by 12pm dispatched the next working day (per their shipping page).

## Philosophy & Quirks

- "We are 100% welsh born and bred"; values of Authentic, Passionate,
  Neighbourly, Pioneering; founded on personal Labrador Dylan (lost July
  2023), with the Silver Lab roast released in tribute.
- Active support of Guide Dogs UK; "Pawsonalise a Coffee" puts a pet's
  portrait on a personalised label of the core coffees.

## Scraping Quirks

- Only the curated `coffee` collection is crawled (16 products, all typed
  `Coffee`); `subscription-plans`, `great-taste` and the personalised-gift
  repackagings are excluded as services/merch/dupes.
- Product pages ARE scraped: products.json lacks altitude/variety/tasting
  notes, which the rendered `div.product-details` "About the coffee" spec
  sheet carries — the soup is pruned to that block.
- The Lab Pack and Lab Duo pairs (`lab-pack`, `lab-duo-*` handles) are flagged
  `is_tasting_kit` / `requires_review` for the admin queue.
- Roast profile is an SVG image, so the roast level may be unextractable.
- Canonical product URLs are `/products/<handle>`.

## Sources

- https://coffilab.co.uk
- https://coffilab.co.uk/pages/our-story
- https://coffilab.co.uk/pages/shipping-returns
- https://coffilab.co.uk/pages/contact-us