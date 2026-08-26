---
type: "Reference"
title: "Prolog Coffee — Roaster Profile"
description: "Copenhagen coffee company combining omni-roasted coffees, four coffee bars, B Corp certification and same-day shipping for orders before 14:00."
---

# Prolog Coffee — Roaster Profile

## Overview

Prolog Coffee is a Copenhagen coffee company with a Shopify storefront, coffee bars, wholesale and education. Its stated vision is to give people better coffee experiences, and its current shop carries seasonal single origins, subscriptions, drip bags and merchandise. The site lists four Copenhagen coffee bars; those retail addresses are not the roastery address.

## Address

- Copenhagen, Denmark — full roastery address not published on site.

## Sustainability

- Prolog’s site links to an impact-commitments page and displays a B Corporation certification badge. The fetched pages did not expose enough detail to describe the underlying commitments without over-interpreting the certification link.

## Schedules & Shipping

- The storefront banner says orders placed before 14:00 receive same-day shipping. A destination-specific shipping-rate table or free-delivery minimum was not published in the fetched pages.

## Philosophy & Quirks

- Prolog describes its core values as “Quality - Life - People - Coffee.” A June 2026 site story explains that the company is “omni roasting” and connects that method to its thinking about quality and equipment.

## Scraping Quirks

- The scraper targets `/collections/buy-our-coffee` and forces collection pages through Playwright, waiting and auto-scrolling to load the infinite-scroll catalogue; product pages use the base fetch path.

## Sources

- https://www.prologcoffee.com
- https://www.prologcoffee.com/pages/about-prolog-full
- https://www.prologcoffee.com/pages/sustainability
- https://www.prologcoffee.com/blogs/news/why-are-we-omni-roasting
