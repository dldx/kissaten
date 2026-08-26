---
type: "Reference"
title: "Oma Coffee Roaster — Roaster Profile"
description: "Hong Kong specialty roaster focused on single-origin espresso, filter coffee and high-end lots, with free domestic delivery above HKD 300."
---

# Oma Coffee Roaster — Roaster Profile

## Overview

Oma Coffee Roaster is a Hong Kong specialty roaster with a Shopify storefront
focused on single-origin espresso, filter coffee and capsules, alongside
equipment and wholesale. Its current catalogue includes high-value lots from
origins such as Ethiopia, Colombia, Kenya and Panama. The reviewed official
pages do not publish a city street address, roasting machine or capacity.

## Address

- Hong Kong — full roastery address not published on site.

## Schedules & Shipping

- The site advertises free domestic shipping for orders of HKD 300 or more. No
  public roast cadence, dispatch day, delivery timeframe or destination-specific
  international rate was found on the reviewed pages.

## Scraping Quirks

- The scraper starts from `/collections/coffee`, uses several Shopify product
  link selectors and runs AI extraction with Playwright enabled. It deliberately
  filters subscriptions, gifts, wholesale, equipment, accessories, merchandise,
  the Option-O products and test roasts, so the catalogue is coffee-only even
  though the collection page contains grinders and other goods.

## Sources

- https://omacoffeeroaster.com
- https://omacoffeeroaster.com/collections/coffee
