---
type: "Reference"
title: "Jet Bean — Roaster Profile"
description: "UK aviation-theme specialty coffee roaster on Shopify at jetbeancoffee.com (canonical; the .co.uk redirects there), roasting single origins inspired by classic aircraft with free UK shipping over £75."
---

# Jet Bean — Roaster Profile

## Overview

Jet Bean (jetbeancoffee.com) is a UK aviation-themed specialty coffee roaster
selling single-origin coffees inspired by classic aircraft from a Shopify
storefront. The canonical domain is jetbeancoffee.com — the older .co.uk
redirects there and the shop was rebuilt on Shopify. The whole-bean catalogue
lives in a curated collection for aviation-lovers and prices are in GBP, with
a £75 free-shipping threshold.

## Address

- Full street address not published on site — United Kingdom.

## Schedules & Shipping

- Free shipping on orders of £75 or more (checkout banner: "Spend £75 for free
  shipping!").

## Scraping Quirks

- Domain correction: jetbeancoffee.co.uk → jetbeancoffee.com (canonical; the
  .co.uk just redirects).
- Shopify with `products.json` served from the curated
  `specialty-coffee-for-aviation-lovers` collection; collection segment is
  stripped to the canonical `/products/<handle>` URL form.
- Pods and merch (Jumbo Jet pods, baseball cap, keyring) are excluded, while
  the "The Flight Deck Collection" — a 3-bag multi-origin sampler — is
  intentionally kept and flagged `is_tasting_kit` so it flows through the
  admin review queue.

## Sources

- https://jetbeancoffee.com
- https://jetbeancoffee.com/collections/specialty-coffee-for-aviation-lovers/products.json
- https://jetbeancoffee.com (checkout banner for free-shipping threshold)