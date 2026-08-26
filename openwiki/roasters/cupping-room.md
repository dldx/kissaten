---
type: "Reference"
title: "Cupping Room — Roaster Profile"
description: "Hong Kong specialty coffee company offering filter and espresso coffees with detailed origin, process and flavour information."
---

# Cupping Room — Roaster Profile

## Overview

Cupping Room is a Hong Kong specialty coffee roasting company. Its shop
organises coffee under Blend and Single Origin products and presents origin,
process, tasting notes and descriptions on product pages. The online shop is a
client-rendered React storefront backed by the GOLS e-commerce service.

## Address

- Hong Kong — full roastery address not published on the consulted site pages.

## Scraping Quirks

- The shop's `Beans` category (`/shop/115`) is rendered by JavaScript, so the
  scraper must use Playwright for listings and product pages. It removes the
  generic `cupping` URL exclusion because the roaster's own domain contains
  that word, and pins extracted currency to HKD because product pages lack an
  `og:price:currency` tag.

## Sources

- https://cuppingroom.hk/
- https://cuppingroom.hk/shop/115
