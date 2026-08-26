---
type: "Reference"
title: "New Ground Coffee — Roaster Profile"
description: "Oxford social enterprise and B Corp training ex-offenders in specialty coffee, on a headless Shopify frontend whose catalogue lives on the myshopify host, with free UK delivery over £25."
---

# New Ground Coffee — Roaster Profile

## Overview

New Ground Coffee (newgroundcoffee.com) is an Oxford-based social enterprise
roaster on a *headless* Shopify setup: the public www site is a custom
SvelteKit frontend, while the machine-readable catalogue lives at
newgroundcoffee.myshopify.com/products.json. The business creates work and
training opportunities for ex-offenders across the UK, describing coffee as
"a catalyst for change" (tagline "Coffee with conviction") and partnering
through The NewGround Foundation. It is one of the UK's first B Corp-
certified coffee roasters, certified carbon neutral, and sells in GBP with
free delivery over £25.

## Address

- Newground Workshop, Oxford, OX3 7BU — United Kingdom (per the site footer).

## Sourcing & Transparency

- Ethically sourced high-grade coffee selected from small-scale farms around
  the world (per their About Us page).
- Certified B Corp — one of the UK's first B Corp-certified coffee roasters.
- Certified carbon neutral: ultra-efficient roasting + renewable energy, with
  the remainder offset through verified schemes; fully recyclable coffee bags.

## Schedules & Shipping

- Free delivery on orders of £25+ (site-wide banner); no roast/dispatch
  cadence published.

## Scraping Quirks

- Headless Shopify quirk: `www.newgroundcoffee.com` serves no public
  `products.json` — the feed is fetched from
  `newgroundcoffee.myshopify.com/products.json` (70 published products) and
  filtered on Shopify's own `product_type == "Coffee"`, which reproduces the
  curated `collections/coffee` collection exactly.
- Coffee-typed Nespresso-compatible pods are excluded by slug (`pods`, `pod`);
  equipment, merch, chocolate, subscriptions and gift cards are non-Coffee
  types and drop out at the type filter.
- The www product page (not the feed's unstructured `body_html`) carries the
  tasting notes, origin, varietal and process, so product pages are scraped
  and pruned to the `ProductMain_product` block.
- Canonical URLs are rewritten to the singular
  `www.newgroundcoffee.com/product/<handle>` form (the plural `/products/`
  form 308-redirects there).

## Sources

- https://www.newgroundcoffee.com
- https://www.newgroundcoffee.com/about-us