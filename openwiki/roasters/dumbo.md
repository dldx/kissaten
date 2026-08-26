---
type: "Reference"
title: "Dumbo Coffee — Roaster Profile"
description: "Taiwan-based Coffee Dumbo specialty roaster using a bilingual Shopline storefront and an AI-assisted catalogue extractor."
---

# Dumbo Coffee — Roaster Profile

## Overview

Coffee Dumbo is a Taiwan-based specialty coffee roaster with Chinese and
English storefront options. The registered scraper identifies the storefront
as Shopline and uses the coffee-bean category at `coffeedumbo.tw`; product
details are extracted with an AI-assisted workflow. The site supplies coffee
products for the catalogue, but the fetched public pages did not expose a
roastery street address or the requested equipment and fulfilment details.

## Address

- Taiwan — city and full roastery address not published on site.

## Scraping Quirks

- Product discovery follows Shopline `/products/` links from the coffee-bean
  category, removes query strings, deduplicates canonical URLs and skips cards
  marked `out-of-stock`.
- Product pages are processed with Playwright and the scraper's optimised AI
  extraction path; translation to English is deliberately disabled in the
  current declaration.

## Sources

- https://www.coffeedumbo.tw
- https://www.coffeedumbo.tw/categories/%E5%92%96%E5%95%A1%E8%B1%86?limit=72
