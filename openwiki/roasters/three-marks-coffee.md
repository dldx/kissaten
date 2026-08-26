---
type: "Reference"
title: "Three Marks Coffee — Roaster Profile"
description: "Barcelona specialty roaster offering origin coffees in 250 g and 1 kg formats, a monthly coffee club and free Spain/Portugal delivery from €30."
---

# Three Marks Coffee — Roaster Profile

## Overview

Three Marks Coffee is a Spanish specialty coffee roaster based in Barcelona. Its Shopify shop offers seasonal single-origin coffees from countries including Brazil, Burundi, Colombia, Ecuador and Kenya, with several coffees available as 250 g or 1 kg bags and with multiple grind choices. The brand also offers the Three Marks Coffee Club subscription and barista training.

## Address

- Moll de la Ronda, 10, 08930 Sant Adrià de Besòs, Barcelona, Spain (Tostadora & Academia / roastery address published on the site)

## Schedules & Shipping

- The storefront states that shipping to Spain and Portugal is free from €30. International shipping is calculated during checkout; no international destination rates are published on the consulted page.

## Philosophy & Quirks

- The shop presents coffees as “marks” and combines a roastery, academy, coffee club and wholesale operation. Product pages expose both bean and grind-size choices rather than treating a coffee as a single undifferentiated SKU.

## Scraping Quirks

- The Shopify scraper reads the site-wide `products.json` endpoint and excludes subscriptions, gift cards, the barista course, coffee bags/capsules, bundles, equipment, merchandise, trays, multipacks and other non-coffee handles. The exclusion list includes numeric pack-size patterns, so new bundle or multipack handles should be checked when maintaining the scraper.

## Sources

- https://www.threemarkscoffee.com
