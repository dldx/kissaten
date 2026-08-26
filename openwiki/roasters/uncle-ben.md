---
type: "Reference"
title: "Uncle Ben's Coffee — Roaster Profile"
description: "Hong Kong specialty roaster and latte-art workshop business with same-day dispatch on Tuesday–Friday orders placed by 10:00."
---

# Uncle Ben's Coffee — Roaster Profile

## Overview

Uncle Ben’s Coffee is a Hong Kong specialty coffee business whose site combines coffee beans, drip bags, cold-brew bags, latte-art workshops and a roastery. Its catalogue is organised by origin and includes coffees from Ethiopia, Yunnan, Nicaragua, Colombia, Burundi, Honduras, Panama, Rwanda, Kenya, Indonesia and Brazil. The site also presents a physical shop in Fortress Hill; that shop address is not used as the roastery address below.

## Address

- Hong Kong, Hong Kong — the consulted site identifies the business as Hong Kong-based but does not publish a separate roastery address.

## Schedules & Shipping

- The storefront banner says orders placed by 10:00 receive same-day dispatch Tuesday–Friday. It also advertises free local San Francisco delivery for orders over HK$500. The site offers several regional currencies, but no complete destination-rate table was visible on the consulted page.

## Scraping Quirks

- The scraper checks three paginated `all-coffee-beans` collection URLs, uses Playwright and targeted screenshots of the `product-info` element (falling back to a full-page screenshot if that element is absent), and skips products whose cards say “Sold out”.
- URL filtering removes gift cards, subscriptions, equipment, grinders, brewing items, merchandise, cups/mugs, filters and apparel. The collection parser assumes a `div.collection` container, so a theme change there would affect discovery.

## Sources

- https://unclebencoffee.com
