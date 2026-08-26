---
type: "Reference"
title: "Fuglen Coffee — Roaster Profile"
description: "Oslo roaster combining Nordic-style coffee with a coffee club, courses and a broad online selection of single-origin lots."
---

# Fuglen Coffee — Roaster Profile

## Overview

Fuglen Coffee is a roastery in Oslo, Norway, with an online Shopify store for coffee, subscriptions, equipment, tea and merchandise. The storefront describes its coffee as roasted fresh weekly for the office subscription and offers a monthly Fuglen Coffee Club. It also publishes brewing guides, cupping and barista-course activities.

## Address

- St. Halvardsgate 33, 0192 Oslo, Norway.

## Schedules & Shipping

- Fuglen says online orders are normally processed within 2–3 business days. Its office-coffee material says coffee is roasted fresh every week. No general free-delivery minimum or destination-specific shipping rate was visible on the accessible pages.

## Philosophy & Quirks

- The store combines a roastery catalogue with courses, cupping and a coffee club; current products are labelled with producer/lot, process, origin and pack size in their names.

## Scraping Quirks

- The scraper targets the availability-filtered coffee collection, selects links with both `/products/` and `CardLink-template`, deduplicates them, and excludes the URL patterns `taste-of-fuglen`, `fuglen-coffee-club`, `christmas` and `drip-bag`. That filter is deliberately narrower than the store’s full coffee-related catalogue.

## Sources

- https://www.fuglencoffee.no
- https://www.fuglencoffee.no/collections/coffee
- https://www.fuglencoffee.no/pages/office-coffee
