---
type: "Reference"
title: "Django Coffee Co — Roaster Profile"
description: "Manchester speciality coffee roaster (Shopify) selling light-roast single origins and blends from a curated coffee collection, plus subscriptions, a Discovery Bundle, equipment and gifts — roasted on a Giesen W15A."
---

# Django Coffee Co — Roaster Profile

## Overview

Django Coffee Co is a Manchester speciality coffee roaster on a Shopify storefront at djangocoffeeco.com, heavily focused on the origin of its coffee and direct trade. The curated `coffee-beans-online-order-coffee-online` collection carries 9 coffee products — single origins such as Tanzania Mondul, Colombia Las Garzas and Ethiopia Guji, plus the Drift Espresso blend and Decaf Colombia El Buho — alongside subscriptions, a Discovery Bundle, equipment and gifts.

## Address

- Manchester, United Kingdom (full street address not published on the site)

## Philosophy & Quirks

- Self-described "Manchester Coffee Roaster" focused on origin and direct trade, with ethically sourced, 100% traceable and transparent coffee.
- Light-to-medium roasts in small batches on a Giesen W15A ("Anna") used for all production roasts.
- One Tree Planted partner — offsets its carbon footprint by planting trees in the Amazon Rainforest.

## Scraping Quirks

- The curated collection is `coffee-beans-online-order-coffee-online` — the site's `/collections/coffee` slug exists but returns 0 products.
- Canonical product URLs are `/products/<handle>` on the `www` host (collection segment stripped, `www` host forced; the bare domain 301s to `www`).
- The `Specials` £5.00 product is out of stock but retained in the catalogue.

## Sources

- https://djangocoffeeco.com
- https://djangocoffeeco.com/collections/coffee-beans-online-order-coffee-online