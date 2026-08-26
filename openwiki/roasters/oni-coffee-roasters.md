---
type: "Reference"
title: "ONI Coffee Roasters — Roaster Profile"
description: "Dublin roastery built by baristas, producing limited-batch coffees with precision profiling."
---

# ONI Coffee Roasters — Roaster Profile

## Overview

ONI Coffee Roasters is a Dublin, Ireland roastery. ONI says it was founded by
coffee professionals and describes its coffees as limited-batch, precisely
profiled and designed to perform across brewing methods. Its shop is a
JavaScript-rendered Next.js storefront.

## Address

- 205B Emmet Road, Inchicore, Dublin 8, D08 EN29, Republic of Ireland.

## Schedules & Shipping

- ONI publishes a flat €5 rate for the Republic of Ireland and €25 for Europe.
  Orders are processed in 1–2 business days; typical transit is 1–3 business
  days in Ireland and 3–7 business days in Europe. The policy lists EU/EEA
  destinations but does not publish a free-delivery threshold.

## Philosophy & Quirks

- ONI's stated premise is that “roasting is not our origin story — brewing is”:
  every batch is designed to bloom, open up and perform regardless of method.

## Scraping Quirks

- The shop listing is server-rendered, but product details are hydrated from
  Next.js RSC data; the scraper therefore uses HTTP for the listing and
  Playwright for product pages, waiting for an `h1`. Product URLs use `/shop/`
  CUIDs rather than normal product paths. Sold-out cards and ONI's “Test Roast -
  Filter” are skipped, and currency is forced to EUR because product pages do
  not expose currency metadata.

## Sources

- https://www.onicoffeeroasters.ie
- https://www.onicoffeeroasters.ie/shipping
