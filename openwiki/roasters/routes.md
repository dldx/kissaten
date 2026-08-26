---
type: "Reference"
title: "Routes Coffee — Roaster Profile"
description: "Oxford, UK specialty coffee roaster on WooCommerce/Divi selling sustainably sourced single origins and blends; routescoffee.co.uk is the UK storefront, distinct from the USD routescoffee.com."
---

# Routes Coffee — Roaster Profile

## Overview

Routes Coffee (routescoffee.co.uk) is an Oxford, UK specialty coffee roaster
running WooCommerce with a Divi builder theme, sourcing sustainably sourced
green beans and selling whole-bean single origins and blends in GBP.

## Address

- Unit 5, Fenchurch Court, Oxford OX4 6ZN, United Kingdom.

## Scraping Quirks

- Domain correction: routescoffee.co.uk is the UK storefront; routescoffee.com
  is a separate USD / North-American storefront.
- WooCommerce REST API (403) and Store API (empty body) are both protected, so
  the HTML catalogue (homepage `#coffee` section) is enumerated with the Yoast
  `product-sitemap.xml` as a resilient second source.
- e2e: 19 saved.

## Sources

- https://routescoffee.co.uk
- https://routescoffee.co.uk/
- https://routescoffee.co.uk/contact-us/