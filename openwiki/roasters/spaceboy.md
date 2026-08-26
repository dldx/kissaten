---
type: "Reference"
title: "Spaceboy Coffee — Roaster Profile"
description: "Edinburgh micro speciality roastery at Holyrood Business Park on Squarespace, roasting single origins, blends, decaf and rare/experimental lots on a hand-built roaster logged in Artisan."
---

# Spaceboy Coffee — Roaster Profile

## Overview

Spaceboy Coffee (spaceboycoffee.co.uk) is a micro speciality coffee roastery
in Edinburgh, working from Holyrood Business Park. The catalogue spans single
origins, blends, a decaf and occasional rare-varietal and experimental lots,
sold from a Squarespace Commerce storefront in GBP alongside subscriptions and
merch.

## Address

- Holyrood Business Park, Edinburgh, EH16 4AP, United Kingdom (published on the
  site's contact block).

## Roasting & Equipment

- The founder's first roaster was hand-built over two years, coming to fruition
  in spring 2021; two thermocouples feed Artisan roast-logging software so
  roast profiles can be replicated accurately (per their About page).

## Scraping Quirks

- Domain correction: `spaceboycoffee.com` redirects to the canonical
  `spaceboycoffee.co.uk`.
- Squarespace shop page does **not** emit `/shop/p/` anchors in the DOM — the
  catalogue is embedded as escaped JSON in the `data-context` attribute of the
  `div[data-controller=ProductList]` element; sold-out cards and the merch
  t-shirt are skipped.
- Prices are exposed via Squarespace's `product:price:currency` meta tag
  (not `og:price:currency`), so GBP is locked up front.
- 6 products saved; no tasting kits in the line-up.

## Sources

- https://spaceboycoffee.co.uk
- https://spaceboycoffee.co.uk/about
- https://spaceboycoffee.co.uk/shop