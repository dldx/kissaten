---
type: "Reference"
title: "Happy Barista — Roaster Profile"
description: "Independent North Yorkshire (small-batch) specialty coffee roaster on a WooCommerce storefront at happybarista.com, hand-roasting a small rotating set of blends and single origins."
---

# Happy Barista — Roaster Profile

## Overview

Happy Barista (www.happybarista.com) is an independent North Yorkshire, UK
small-batch specialty coffee roaster, formerly trading as happybarista.co.uk
and now serving from a live WordPress + WooCommerce storefront (canonical www).
The catalogue is a small rotating set of whole-bean blends and single origins —
about six distinct coffees including The Good Morning Blend and The Keepin'
Me Happy Blend — plus a Swiss Water decaf and a coffee subscription, priced in
GBP.

## Address

- Happy Barista Coffee Company Ltd, Unit 22, Thirkill Park, Pannal, North
  Yorkshire, HG3 1GQ — United Kingdom. (Published in the site footer;
  Registered in England & Wales No.13625496.)

## Sourcing & Transparency

- Swiss Water Process decaffeination used for its decaf offering (per product
  listing).

## Scraping Quirks

- Domain correction: happybarista.co.uk → www.happybarista.com (canonical www).
- WooCommerce storefront scraped from the `/shop/` product category, using
  the WooCommerce `outofstock` card class to skip sold-out products (2 of the
  6-catalogue coffees were sold-out at e2e; 4 saved, 0 kits).
- The theme renders duplicate product cards across several `ul.products`
  grids; the scraper deduplicates collected product URLs.

## Sources

- https://www.happybarista.com
- https://www.happybarista.com/shop/
- https://www.happybarista.com (footer address)