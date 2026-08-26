---
type: "Reference"
title: "The Coffee Apothecary — Roaster Profile"
description: "Scottish specialty coffee roastery with cafés in Udny and Ellon, Aberdeenshire, selling a curated 12-coffee collection from the shop.thecoffeeapothecary.co.uk Shopify storefront."
---

# The Coffee Apothecary — Roaster Profile

## Overview

The Coffee Apothecary is a Scottish specialty coffee roastery with roastery /
cafés in Udny and Ellon, Aberdeenshire. Its curated `coffee-beans` Shopify
collection carries 12 whole-bean coffees (each with 250 g / 1 kg variants) in
GBP, sold from shop.thecoffeeapothecary.co.uk — while the `www` subdomain is a
separate brand site. Extraction is JSON-only from the rich Shopify `body_html`.

## Address

- Roastery and cafés in Udny & Ellon, Aberdeenshire, United Kingdom. The site
  lists the locations as Udny (AB41 7PQ) and 21 The Square, Ellon (AB41 9JB);
  no separate roastery street address is published.

## Scraping Quirks

- Domain correction: the canonical storefront is shop.thecoffeeapothecary.co.uk
  — the `www.thecoffeeapothecary.co.uk` host is a separate brand site.
- Shopify JSON-only from the curated `coffee-beans` collection; URL
  canonicalized to the no-collection `/products/<handle>` form.
- The "Fermentation Project" is a whole-bean coffee in the curated bean
  collection, but the AI (Gemini) flagged it `is_tasting_kit` /
  `requires_review` — a false positive that lands it in the admin review queue.
- e2e: 12 saved + 1 kit flag (the Fermentation Project false positive).

## Sources

- https://shop.thecoffeeapothecary.co.uk
- https://shop.thecoffeeapothecary.co.uk/collections/coffee-beans
- https://shop.thecoffeeapothecary.co.uk/pages/wholesale