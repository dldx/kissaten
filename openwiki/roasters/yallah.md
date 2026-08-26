---
type: "Reference"
title: "Yallah Coffee — Roaster Profile"
description: "Cornwall specialty roaster at Argal Home Farm, Falmouth roasting single-origin coffees 'from our barn', with cafés in St Ives and Penryn, on a Shopify storefront whose edge needed a curl_cffi TLS fingerprint fix."
---

# Yallah Coffee — Roaster Profile

## Overview

Yallah Coffee (yallahcoffee.co.uk) is a Cornwall specialty coffee roaster based
at Argal Home Farm, Falmouth, roasting and sourcing single-origin coffees
"from our barn in Cornwall" on a Shopify storefront. The whole-bean catalogue
(~11 coffees saved) is mostly single origins — Peru, Colombia, Guatemala,
Mexico and Brazil — alongside a Brazil house espresso and a Mexican house
decaf. It runs cafés in St Ives (Court Arcade) and Penryn (inside Work Shop
Studios).

## Address

- Argal Home Farm, Kergilliack, Falmouth, Cornwall, TR11 5PD — United Kingdom
  (the roastery; open Mon–Fri 8am–4pm, per their site).

## Philosophy & Quirks

- "We believe that coffee and business can be a force for positive change"
  (their vision), roasting proudly from a barn in Cornwall.

## Scraping Quirks

- `product_type` is inconsistent (beans carry both `Coffee` and `coffee`), so
  the scraper uses a token-based non-bean exclusion (subscriptions, cold-brew,
  non-bean bundles) instead of trusting the type, letting tasting-kit samplers
  flow through to the review queue rather than being dropped.
- The "Taster pack — Three of the best" (`triple-pack-bundle`) sampler did not
  survive extraction and is not among the 11 saved beans (flag extractor
  failure, not a catalogue delist).
- The edge rejects curl_cffi's default libcurl TLS fingerprint (403 on
  products.json) — the scraper rebuilds its client with `impersonate="chrome"`
  (mirrors twoday.py).

## Sources

- https://yallahcoffee.co.uk
- https://yallahcoffee.co.uk/pages/locations
- https://yallahcoffee.co.uk/pages/our-story