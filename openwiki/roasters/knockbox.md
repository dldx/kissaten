---
type: "Reference"
title: "Knockbox — Roaster Profile"
description: "Hong Kong roaster offering separate filter and espresso roast selections, with weekly roasting and free local shipping over HK$500."
---

# Knockbox — Roaster Profile

## Overview

Knockbox is a specialty coffee roaster and café business in Hong Kong. Its Wix storefront separates coffee into filter and espresso roasts, and also carries equipment, workshops and subscriptions. The site describes its filter coffees as light roasts for manual brewing and its espresso coffees as darker, caramelisation-focused roasts.

## Address

- Hong Kong, Hong Kong — the site identifies Hong Kong as the roasting location but does not publish a separate roastery address; the listed café addresses are not used here.

## Schedules & Shipping

- The site says coffee is **freshly roasted in Hong Kong weekly**.
- The storefront banner states **free shipping on orders over HK$500**. No delivery timeframe or destination-specific rates were verified.

## Philosophy & Quirks

- Knockbox presents filter and espresso as deliberately different roast approaches: filter roast is intended to preserve nuance and terroir, while espresso roast emphasises caramelisation, complexity and sweetness.

## Scraping Quirks

- The scraper handles Wix’s `/product-page/` URLs and walks a product card’s ancestors to identify `Out of stock` items. It also trims product-page HTML to the text-bearing Wix `TPAMultiSection_` container before AI extraction, and excludes URL matches for capsules, drip bags, tools, glassware, machines, Outin, subscriptions and ICO products.

## Sources

- https://www.knockboxcoffee.hk
- https://www.knockboxcoffee.hk/coffee
- https://www.knockboxcoffee.hk/about
- https://www.knockboxcoffee.hk/contact-us
