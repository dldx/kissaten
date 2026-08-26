---
type: "Reference"
title: "The Bean Shop — Roaster Profile"
description: "Family-run Perth (Scotland) specialty coffee roaster, established 2003 by John and Lorna Bruce, roasting on a 5 kg Probat in the basement of its 67 George Street shop."
---

# The Bean Shop — Roaster Profile

## Overview

The Bean Shop (thebeanshop.co.uk) is a family-run specialty coffee roaster in
Perth, Scotland, established in 2003 by husband-and-wife John and Lorna Bruce
(per their About page). It started roasting in the basement of its George
Street shop on a 5 kg Probat roaster and now sells a curated selection of
single origins and blends from a Shopify storefront in GBP.

## Address

- 67 George Street, Perth, PH1 5LB, United Kingdom (published in the site
  footer).

## Roasting & Equipment

- Coffee has been roasted in the basement of the George Street shop on a 5 kg
  Probat roaster since the roastery began (per the About page).

## Scraping Quirks

- Shopify JSON-only from the curated `collections/coffee` products.json; URLs
  canonicalized to the no-collection `/products/<handle>` form.
- The curated collection mixes in a few non-bean items: Moka/stovetop brewers
  are excluded by slug and subscriptions by the base title filter.
- The taster boxes (Blends Taster Box, Origins Taster Box) are kept and flagged
  `is_tasting_kit` / `requires_review` into the review queue, never excluded.
- e2e: 19 whole-bean coffees saved; 5 blend products persistently failed
  extraction.

## Sources

- https://thebeanshop.co.uk
- https://thebeanshop.co.uk/pages/about-us
- https://thebeanshop.co.uk/collections/coffee