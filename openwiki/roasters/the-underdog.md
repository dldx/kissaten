---
type: "Reference"
title: "The Underdog — Roaster Profile"
description: "Athens specialty coffee roaster and café selling espresso and filter coffees from a WooCommerce storefront, with a catalogue split between two coffee categories."
---

# The Underdog — Roaster Profile

## Overview

The Underdog is a specialty coffee roaster based in Athens, Greece. Its WooCommerce shop separates coffee into **Espresso** and **Filter Coffee** categories. The official pages were not available to the research fetcher, so this profile limits itself to the location and shop structure recorded in the project scraper and checklist.

## Address

- Athens, Greece — full roastery address not published on the accessible site pages.

## Scraping Quirks

- The scraper uses the two WooCommerce category URLs `/shop/category/espresso/` and `/shop/category/filter-coffee/`, fetches them without Playwright, removes products whose surrounding text says “Out of stock” or “Sold out”, and excludes URL patterns containing `subscription`, `gift`, `giftcard`, `merch`, `equipment` or `brew`.
- Product extraction is AI-powered and the post-processing step pins the currency to EUR.

## Sources

- https://www.underdog.gr
- https://www.underdog.gr/shop/category/espresso/
- https://www.underdog.gr/shop/category/filter-coffee/
