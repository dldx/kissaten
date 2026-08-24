---
type: "Reference"
title: "Kapow Coffee — Roaster Profile"
description: "Leeds specialty roaster on Shopify roasting and serving in Leeds since 2013, with a curated six-bean catalogue — Kapow Blend, three single origins and two decafs — sold from a Thorntons Arcade café."
---

# Kapow Coffee — Roaster Profile

## Overview

Kapow Coffee (kapowcoffee.co.uk) is a Leeds specialty coffee roaster that has
been roasting and serving coffee in Leeds since 2013 (per their site), on a
Shopify storefront in GBP. The whole-bean catalogue is small and curated — six
products: the Kapow Blend house blend (50/50 natural Brazil and Ethiopia), three
single origins (Uganda Gombe, Uganda Imbalu, Brazil Cocarive Co-operative) and
two decafs (Uganda Rwenzori, Colombia Mustafa).

## Address

- 15 Thorntons Arcade, Leeds, LS1 6LQ — United Kingdom (café).

## Schedules & Shipping

- Roasts are made Mondays and Thursdays, with deliveries sent out Wednesdays and
  Fridays; deliveries take 3–5 days (per the site banner).
- UK orders ship Royal Mail 1st class and usually arrive in 1–3 working days
  (up to 2–4 business days processing, per the shipping policy).
- Not shipping abroad at the time of writing; no free-delivery minimum published.

## Scraping Quirks

- Shopify; only the curated `coffee-beans` collection is scraped — 6 live
  products, while `collections.json`'s `products_count` is stale (claims 8).
- JSON-only extraction; canonical product URLs are `/products/<handle>`
  (collection segment stripped). Currency is pinned to GBP.

## Sources

- https://kapowcoffee.co.uk
- https://kapowcoffee.co.uk/collections/coffee-beans
- https://kapowcoffee.co.uk/pages/shops
- https://kapowcoffee.co.uk/policies/shipping-policy
