---
type: "Reference"
title: "Fjord Coffee — Roaster Profile"
description: "Berlin-based Fjord Coffee Roasters, a Shopify specialty coffee shop whose scraper deliberately excludes its named taster set."
---

# Fjord Coffee — Roaster Profile

## Overview

Fjord Coffee Roasters is a specialty coffee roaster based in Berlin, Germany.
The storefront at `fjord-coffee.de` is Shopify-based and prices its coffee in
EUR. Its coffee collection is the registered catalogue source. The company is
described by its registration as focused on quality and sustainability, but the
public pages fetched for this profile did not provide enough concrete detail to
state a particular initiative.

## Address

- Berlin, Germany — full roastery street address not published on site.

## Scraping Quirks

- The scraper uses standard HTTP extraction rather than Playwright and searches
  multiple Shopify product-card selectors.
- The product URL containing `fjord-taster-set` is explicitly excluded. This
  named rule must not be broadened into a generic exclusion of all tasting kits
  without checking the review-queue policy.

## Sources

- https://fjord-coffee.de
- https://fjord-coffee.de/collections/coffee
