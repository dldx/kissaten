---
type: "Reference"
title: "Lost Barn Coffee — Roaster Profile"
description: "Cheshire farm micro-roastery at Old Hall Farm, Tilston, named after a barn blown away in the storm of January 1839, on a WooCommerce storefront with free delivery over £40."
---

# Lost Barn Coffee — Roaster Profile

## Overview

Lost Barn Coffee (lostbarncoffee.co.uk) is a small-batch Cheshire farm
micro-roastery at Old Hall Farm, Grafton, Tilston, Malpas, near the site of a
barn that — per their story — was "blown away" in the catastrophic storm of
January 1839. It ethically sources beans and roasts them in small batches on a
copper roaster, offering whole-bean blends and single origins (several limited
editions) plus sampler boxes from a WordPress + WooCommerce storefront in GBP.

## Address

- The Lost Barn Coffee Roasters, Old Hall Farm, Grafton, Tilston, Malpas,
  Cheshire, SY14 7JE, United Kingdom (per the contact page).

## Schedules & Shipping

- Free delivery on all orders over £40 (stated site-wide).

## Philosophy & Quirks

- The name (and café) trace to a barn "blown away" in the storm of January
  1839 on the Cheshire estate; the micro-roastery grew up a century and a half
  later next to its site.

## Scraping Quirks

- WooCommerce public Store API discovery (santu / casa pattern): no HTML
  scanning; sold-out detection via the API's `is_in_stock` flag; filter keeps
  only the `coffee` and `sample-boxes` categories.
- The non-`www` host is canonical; `www.lostbarncoffee.co.uk` 301-redirects.
- Sampler boxes are intentionally kept and flagged `is_tasting_kit` /
  `requires_review` into the review queue (7 sample-box products at e2e).
- "The Fermentation Project" is a whole-bean coffee in the `coffee` category,
  but the AI (Gemini) flagged it as a kit — a false positive in the queue.

## Sources

- https://lostbarncoffee.co.uk
- https://lostbarncoffee.co.uk/contact/
- https://lostbarncoffee.co.uk/our-story/