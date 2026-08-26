---
type: "Reference"
title: "Humpback Whale Coffee — Roaster Profile"
description: "Munich specialty coffee project built around single-origin coffees, named origins and fresh roast-to-order dispatch."
---

# Humpback Whale Coffee — Roaster Profile

## Overview

Humpback Whale Specialty Coffee is a Munich, Germany coffee project run from a café and online shop. The founders describe a journey through Vietnam, Australia, the Netherlands and Germany before settling in Munich. Its coffee menu is single-origin, with country, region and producer named wherever possible; the storefront is a Next.js site rather than a conventional hosted shop platform.

## Address

- Munich, Germany — the consulted site publishes the café address but does not identify a separate roastery address.

## Sourcing & Transparency

- The company says it names the country, region and producer wherever it can, and presents “real farm stories” and tasting notes. No price-paid-to-producer figures or cost breakdown were published on the consulted pages.

## Schedules & Shipping

- Coffee is roasted to order and shipped fresh from Munich. Free shipping within Germany is advertised for orders over €50; no other destination-specific rates were published on the consulted pages.

## Philosophy & Quirks

- The name is intentionally open-ended: the founders say the whale can evoke home, the sea, freedom, curiosity and kindness. Lucy, the co-founder and Germany’s 2025 Cup Tasters Champion, runs the bar.

## Scraping Quirks

- Product pages are a Next.js App Router application whose useful product data is embedded in a `self.__next_f.push` Flight script. The scraper selects the script containing both the product slug and a `coffee` object, then sends that script to the AI extractor instead of the full page HTML.

## Sources

- https://humpbackwhalecoffee.com/about
- https://humpbackwhalecoffee.com/impressum
- https://humpbackwhalecoffee.com
