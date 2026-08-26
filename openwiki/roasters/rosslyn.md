---
type: "Reference"
title: "Rosslyn Coffee — Roaster Profile"
description: "City of London café chain on Shopify roasting a curated line of whole-bean coffees (for milk, black and filter brewing, plus a Financial Times special-edition single origin) with free UK shipping over £15 and a thin 4-coffee online catalogue."
---

# Rosslyn Coffee — Roaster Profile

## Overview

Rosslyn Coffee (rosslyncoffee.com) is a London café chain on Shopify, praised
on its own site as "the best coffee shop in the City of London" and "the best
worst kept secret in the City of London". It operates cafés across the City of
London and roasts a curated line of whole-bean coffees for home: coffees
roasted for milk, black and filter brewing, plus a Financial Times 'Daily
Scoop' special-edition single origin — a genuinely thin 4-product online
catalogue, since Rosslyn is primarily an in-person café chain.

## Address

- No separate roastery address published on site; seven café addresses are
  published on their /pages/visit, all in the City of London — e.g.
  78 Queen Victoria Street, London EC4N 4SJ and 21 Royal Exchange,
  City of London EC3V 3LP — United Kingdom.

## Schedules & Shipping

- Free shipping for coffee orders over £15 ("coffee delivery in London",
  per their shipping policy).
- Order before the previous day and your coffee goes out first-class via
  Royal Mail, Monday – Friday; orders placed Saturday and Sunday are
  dispatched on Monday.

## Scraping Quirks

- The whole-bean coffee lives only in the curated `coffee-for-home`
  collection (4 products); mugs, coffee vouchers and gift subscriptions sit
  in other collections and never appear in the coffee payload, so the bean
  catalogue is genuinely thin.
- No product types are set on the coffees, so the slug exclude-list is the
  primary net for any non-coffee that might surface.

## Sources

- https://www.rosslyncoffee.com
- https://www.rosslyncoffee.com/pages/visit
- https://www.rosslyncoffee.com/policies/shipping-policy