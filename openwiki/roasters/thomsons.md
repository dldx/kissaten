---
type: "Reference"
title: "Thomson's Coffee — Roaster Profile"
description: "Glasgow coffee roaster traced to David Thomson's 1841 shop on St Vincent Street, selling house blends (1841, St. Vincent Roast, Renfield 35) and single origins from a Shopify storefront at thomsonscoffee.com."
---

# Thomson's Coffee — Roaster Profile

## Overview

Thomson's Coffee (www.thomsonscoffee.com) is a Glasgow roaster that traces its
roots to 1841, when 24-year-old David Thomson, a tea and coffee merchant from
Edinburgh, relocated to Glasgow and set up his inaugural shop on St Vincent
Street (per the site's history page). It roasts house blends — 1841, St.
Vincent Roast, Renfield 35, TEAM — alongside single origins, sold from a
Shopify storefront in GBP.

## Address

- Roastery in Glasgow, United Kingdom — full roastery street address not
  published on the site. Its cafés are at 211 Fenwick Road, Giffnock, Glasgow
  G46 6JD and 14 Vinicombe Street, Glasgow G12 8BG (per the locations page).

## Philosophy & Quirks

- Founded 1841 by David Thomson; blends are named after the company's history
  (1841) and Glasgow landmarks (St. Vincent, Renfield 35, TEAM).

## Scraping Quirks

- Shopify JSON-only from the curated `/collections/coffee` collection;
  non-bean and subscription products (gift cards, wholesale, equipment,
  capsules, chocolate, syrup, barista kits) excluded by slug; canonical
  no-collection URLs.
- Sold-out coffees are reflected in stock status within the saved set (2
  sold-out at e2e).
- "The Fermentation Project" is a whole-bean coffee in the curated collection,
  but the AI (Gemini) flagged it `is_tasting_kit` / `requires_review` — a
  false positive landing in the admin review queue. e2e: 20 saved + 1 kit.

## Sources

- https://www.thomsonscoffee.com
- https://www.thomsonscoffee.com/pages/history
- https://www.thomsonscoffee.com/collections/coffee