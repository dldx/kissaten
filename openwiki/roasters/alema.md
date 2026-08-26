---
type: "Reference"
title: "Alema Coffee — Roaster Profile"
description: "Bury St Edmunds, Suffolk family roaster sourcing premium single-origin coffee directly from its family-owned farm in Ethiopia, sold whole-bean from a Wix storefront."
---

# Alema Coffee — Roaster Profile

## Overview

Alema Coffee (alemacoffee.com) is a family roaster in Bury St Edmunds, Suffolk,
selling whole-bean coffees from a Wix storefront in GBP. Per their site they
source premium single-origin coffee directly from their family-owned farm in
Ethiopia, with a shop on Abbeygate Street.

## Address

- 61 Abbeygate Street, Bury St Edmunds, Suffolk IP33 1LB, United Kingdom
  (roastery shop address published on the site).

## Scraping Quirks

- Wix storefront; the whole-bean catalogue is enumerated from the paginated
  `/category/all-products` listing (`?page=2`).
- alemacoffee.com's edge resets the HTTP/2 stream for curl_cffi's default TLS
  fingerprint, so the client is rebuilt with `impersonate="chrome"`.
- e2e: 17 coffees saved, no tasting-kit flags (any future sampler would be
  flagged into the admin review queue rather than excluded).

## Sources

- https://www.alemacoffee.com
- https://www.alemacoffee.com/contact
- https://www.alemacoffee.com/category/all-products