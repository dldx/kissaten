---
type: "Reference"
title: "Wogan Coffee — Roaster Profile"
description: "Bristol family coffee roaster (not the Cardiff bean-to-bar shop) roasting ethically sourced beans for over fifty years, selling a curated whole-bean range from a Shopify storefront."
---

# Wogan Coffee — Roaster Profile

## Overview

Wogan Coffee (wogancoffee.com) is a family coffee roaster in Bristol — the
premium whole-bean range, not the Cardiff bean-to-bar shop — established by
the bowler-hatted Mr Wogan over fifty years ago. It sources and roasts
ethically sourced coffee and sells a curated whole-bean range from a Shopify
storefront in GBP.

## Address

- Roastery & Production Headquarters: 5-8 Elton Street, Bristol BS2 9EH, United
  Kingdom. (Their shop, brew bar & training campus is at Bourbon House, 2-11
  Clement Street, Bristol BS2 9EQ.)

## Scraping Quirks

- wogancoffee.com's edge rejects curl_cffi's default TLS fingerprint (HTTP 403
  on every attempt), so the client is rebuilt with `impersonate="chrome"`.
- Shopify products.json from the curated `all-coffee` collection; pod products
  (`-coffee-pods`) are excluded.
- 3 curated TASTER PACK kits are retained and flagged `is_tasting_kit` /
  `requires_review`. The "Fermentation Project" is a whole-bean coffee that
  Gemini false-flagged as a kit — another review-queue entry.
- The "omega" roast persistently fails extraction (out-of-stock updates
  guarded).
- e2e: 35 saved + 4 kit flags (3 genuine TASTER PACKs + the Fermentation
  Project false positive).

## Sources

- https://wogancoffee.com
- https://wogancoffee.com/pages/contact
- https://wogancoffee.com/collections/all-coffee