---
type: "Reference"
title: "Smith Street Coffee Roasters — Roaster Profile"
description: "Sheffield roastery & coffee shop at Unit 1, Hope Works founded 2014 on a Wix storefront, roasting and shipping Monday to Friday with free Track 48 delivery over £30."
---

# Smith Street Coffee Roasters — Roaster Profile

## Overview

Smith Street Coffee Roasters (smithstreetcoffeeroasters.co.uk) is a Sheffield
specialty roastery and coffee shop ("fanatics since 2014", per their site)
operating from Hope Works on Sussex Road. It sells blends, single origins,
decaf, seasonal releases, coffee bundles and a tasting-flight sampler from a
Wix storefront in GBP, alongside subscriptions, courses and coffee kit.

## Address

- Unit 1, Hope Works, Sussex Road, Sheffield S4 7YQ, United Kingdom
  (roastery & coffee shop, published on the site).

## Sustainability

- The site's sustainability page highlights recyclable & CO₂-neutral packaging,
  low-carbon-footprint shipping and supporting eco-conscious farming, and the
  roastery is a Roasters Guild member (per their site).

## Schedules & Shipping

- Roasts and ships 5 days a week, Monday to Friday; orders placed before
  midnight are roasted and packed the next working day (per their site).
- Free Royal Mail Tracked 48 shipping on orders over £30.

## Scraping Quirks

- Wix storefront; discovery is via the store-products sitemap because category
  pages render their product tiles client-side.
- Substantial non-coffee inventory (teas, mugs, cups, pods, gift certificates,
  equipment, apparel) is filtered out, leaving the ~19 coffee/bundle/sampler
  URLs from a 62-product sitemap.
- The TASTING FLIGHT sampler is retained and flagged `is_tasting_kit` /
  `requires_review` into the admin review queue (never excluded).
- 17 coffee products saved; 2 entries recur as persistent AI-extraction
  failures (guarded out-of-stock updates).

## Sources

- https://www.smithstreetcoffeeroasters.co.uk
- https://www.smithstreetcoffeeroasters.co.uk/who-we-are-story
- https://www.smithstreetcoffeeroasters.co.uk/shipping-info