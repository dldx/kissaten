---
type: "Reference"
title: "Cuppers Choice — Roaster Profile"
description: "Sheffield specialty coffee roaster on Shopify at cupperschoice.coffee, known for distinctive, technically processed single origins (anaerobic naturals, thermic/thermal-shock lots, red honey) and a sugarcane decaf, roasted on IRM machines."
---

# Cuppers Choice — Roaster Profile

## Overview

Cuppers Choice is a Sheffield specialty coffee roaster on a Shopify storefront at
cupperschoice.coffee (the `.co.uk` host 301-redirects there). Founded in 2019
by brothers Jasper and Harley with Jordan of Whaletown Coffee, it began roasting
in Feb 2020 and is known for technically challenging single origins — anaerobic
naturals, "thermic" and thermal-shock lots, red honey — plus a sugarcane decaf,
with the Players Gold house blend (Rwanda / Costa Rica). Roasted on IRM machines
and sold whole-bean, with a curated `coffee` collection of ~13 beans.

## Address

- 169 Rutland Road, Sheffield S3 9PT — United Kingdom

## Sourcing & Transparency

- Mission: "high-grade coffee that is ethically and sustainably sourced", using
  the business as a force for good for environmental protection, social justice
  and economic development in coffee-growing communities (per their site).
- Partnership only with producers, exporters and importers that prioritise
  transparency; coffee is "fully traceable from farm to cup". They decline to
  label it a universal "ethical"/"Fairtrade" marker, preferring per-product stories.

## Roasting & Equipment

- Roasted on IRM 30 and 3kg roasters in Sheffield; every coffee profiled and
  cupped in-house before QC ("look for the diamond — our seal of approval");
  started on a Loring S15 at Steve Penk's facility in Feb 2020.

## Schedules & Shipping

- Roasted to order (per their FAQ); free UK shipping over £50 (banner); ships
  worldwide. 250g bags are PCR recycled plastic, recyclable with soft plastics.

## Scraping Quirks

- Domain correction: `cupperschoice.co.uk` → `cupperschoice.coffee` (Shopify
  301), the canonical host the scraper uses everywhere.
- A single curated `coffee` collection is scraped (14 → 13 beans): the digital
  gift card typed `Coffee` is excluded by slug; the Darkroom chocolate bar,
  mis-typed `Coffee` in Shopify, sits in no collection so is never fetched.
- `collections.json` reports stale counts (e.g. 111 vs 14) — only
  `products.json` counts are authoritative.
- GBP pinned against Shopify Markets geolocation.

## Sources

- https://cupperschoice.coffee
- https://cupperschoice.coffee/pages/our-story
- https://cupperschoice.coffee/pages/mission
- https://cupperschoice.coffee/pages/contact-us
- https://cupperschoice.coffee/pages/faqs