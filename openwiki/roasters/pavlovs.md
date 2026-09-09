---
type: "Reference"
title: "Pavlov's Coffee — Roaster Profile"
description: "One-person Cape Town micro-batch roaster of single-origin, often organic coffees, with roast-to-preference customisation and a Pavlovian coffee-ritual namesake."
---

# Pavlov's Coffee

## Overview

Pavlov's Coffee is a micro-batch roaster in Cape Town, South Africa offering
single-origin beans — organic where possible — at "prices that won't break the bank".
It is a small, personal operation: the founder describes starting the brand out of
care about what goes into their body (pesticides on food and drink) and treats coffee
as a daily ritual. The storefront is a WordPress/WooCommerce shop with a tiny,
rotating catalogue of single origins (Burundi, Honduras, Colombia and Brazil at
review time). There is no shop front yet; sales are online only.

## Address

- Cape Town, South Africa — full address not published on site ("We don't have a shop front yet, but soon!")

## Philosophy & Quirks

The name encapsulates the founder's "personal obsession influenced by the enchantment
of repetition": coffee as a joyful ritual and mental cue. Micro-batch roasting lets
them bring in small quantities and customize the roast to a customer's preference, and
they invite customers to email requests for specific coffees — "if one person wants
it, there are many more who will follow". Contact is by cell/WhatsApp (060 633 7783)
or email (Pavlov@pavlovscoffee.co.za).

## Scraping Quirks

- Very small catalogue (four products at scraper-authoring time); the `/shop/`
  archive and `/product-category/coffee/` list the same items, and the shop archive
  leaks `/shop/feed/` RSS links that the scraper filters.
- The theme (OceanWP) does not put a `product` class on the listing cards, so
  extraction keys on the `woocommerce-LoopProduct-link` anchors.

## Sources

- https://pavlovscoffee.co.za/ (home)
- https://pavlovscoffee.co.za/who-we-are/ (About us)
- https://pavlovscoffee.co.za/contact/
- https://pavlovscoffee.co.za/product-category/coffee/
