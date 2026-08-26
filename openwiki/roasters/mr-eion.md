---
type: "Reference"
title: "Mr Eion — Roaster Profile"
description: "Edinburgh speciality coffee roaster (since 2013) on Shopify roasting single origins and house blends imported by B Corp D.R. Wakefield, sold from Stockbridge and Trinity shops."
---

# Mr Eion — Roaster Profile

## Overview

Mr Eion Coffee Roaster (mreion.com) is an Edinburgh, Scotland speciality
coffee roaster on a Shopify storefront in GBP, small-batch roasting single
origins and house blends (Stockbridge Blend, Tiger Paws) as whole beans or
ground. The company opened in 2013 and is a mixed merchant — alongside coffee
it sells tea & infusions, brewers, filters and merch from its two Edinburgh
sites.

## Address

- Stockbridge Shop — 9 Dean Park Street, Edinburgh, EH4 3NG — United Kingdom.
- Trinity Shop & roastery — 44-44a East Trinity Road, Edinburgh, EH5 3DJ —
  United Kingdom.

## Sourcing & Transparency

- Roasts coffee imported by D.R. Wakefield, a B Corporation, and has worked
  with them since opening in 2013; Mr Eion itself is not (yet) a B Corp but
  relies on its importer's certification for sustainably and ethically
  sourced beans (per their About Us page).

## Schedules & Shipping

- Stockbridge Shop open Tue–Sat and Trinity Shop Tue–Sat (per their contact
  page); no roast cadence or free-delivery threshold published.

## Scraping Quirks

- Shopify products.json: the root feed carries 27 products but only 13 are
  `product_type == "Coffee"` — the rest are tea, equipment, merch and gift
  cards — so the scraper filters on the Coffee type and excludes the
  `roasters-choice` ongoing subscription by slug.
- Ghost collections exist ("Coffee - House Blends", "Myanmar", "New
  Products" return 0), so collection metadata is not trusted and the whole
  root feed is filtered instead.
- Thin product pages (no structured origin/process block) mean JSON-only
  extraction. Currency is pinned to GBP to stop geo-conversion.

## Sources

- https://mreion.com
- https://mreion.com/pages/about-us
- https://mreion.com/pages/contact