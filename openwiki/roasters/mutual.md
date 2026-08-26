---
type: "Reference"
title: "Mutual Coffee Roasters — Roaster Profile"
description: "Edinburgh micro-roastery on Shopify selling ten whole-origin coffees in GBP, roasting and shipping fresh every Monday, with subscriptions shipped free."
---

# Mutual Coffee Roasters — Roaster Profile

## Overview

Mutual Coffee Roasters (mutualcoffee.co.uk, canonical apex — www 301s to it)
is an Edinburgh micro-roastery on a Shopify storefront priced in GBP. It
sells a curated retail range of ten whole-bean coffees — single origins such
as San Pedro Necta (Guatemala), Kigeri Washed/Natural and Shyira (Rwanda),
plus decaf — sourced for taste and positive producer impact, alongside
coffee subscriptions and wholesale.

## Address

- Edinburgh — full street address not published on site (the site confirms
  the Edinburgh location on its homepage but publishes no street address).

## Sourcing & Transparency

- As a small business it can't buy enough to buy directly from producers, so
  it works with "a few trusted importers" that deliver positive impact for
  producers, and is always clear about who it purchased coffee from (per
  their FAQ/contact page).

## Schedules & Shipping

- Fresh coffee shipped every Monday (homepage banner); free shipping on all
  subscriptions (homepage banner). No free-delivery threshold published for
  one-off orders.

## Scraping Quirks

- The root products.json mixes 10 retail coffees with 11 `Wholesale`-typed
  duplicates, 3 subscriptions (15 variants each) and a cap; wholesale handles
  don't reliably carry a "wholesale" token, so only the curated
  `collections/new-coffee` page is scraped (the naive `/collections/coffee`
  handle is empty).
- The wholesale-only Shyira Natural is intentionally not scraped — it is not
  part of the retail catalogue.
- No structured origin/process block on product pages → JSON-only
  extraction; currency pinned to GBP.

## Sources

- https://mutualcoffee.co.uk
- https://mutualcoffee.co.uk/pages/contact