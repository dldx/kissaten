---
type: "Reference"
title: "Sunday Coffee Roasters — Roaster Profile"
description: "Hampshire roastery trading as Sunday Roastery Ltd from the Old Chicken Shed, Southbourne/Emsworth, on Squarespace with seasonal single origins, blends and a rotating coffee taster box."
---

# Sunday Coffee Roasters — Roaster Profile

## Overview

Sunday Coffee Roasters (sundaycoffee.co.uk) is an independent specialty
roastery based in Southbourne/Emsworth, Hampshire, trading as Sunday Roastery
Ltd (per the site footer and Organization metadata). It sources, roasts and
sells seasonal specialty coffees — single origins, blends and a rotating
coffee taster box — from a Squarespace storefront in GBP.

## Address

- Sunday Roastery Ltd, Old Chicken Shed, Main Road, Southbourne, Emsworth
  PO10 8JN, United Kingdom (published on the site footer).

## Scraping Quirks

- Squarespace; products live at `/coffees/...` and carry the standard
  product-page meta tags plus a `static-context` variants JSON.
- Merchandise (mugs, tote bags, apparel) is excluded; the Coffee Taster Box v3
  sampler is retained and flagged `is_tasting_kit` / `requires_review` into
  the admin review queue (never excluded).
- 8 products saved; 1 entry recurs as a persistent AI-extraction failure
  (guarded out-of-stock updates).

## Sources

- https://sundaycoffee.co.uk
- https://sundaycoffee.co.uk/coffees
- https://sundaycoffee.co.uk/contact