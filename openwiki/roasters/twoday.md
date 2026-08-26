---
type: "Reference"
title: "TwoDay Coffee Roasters — Roaster Profile"
description: "Bristol (St Michael's Hill) speciality coffee roaster on a custom e-commerce storefront, founded by a couple who lived in Tokyo and New Orleans, roasting fresh to order for home and office."
---

# TwoDay Coffee Roasters — Roaster Profile

## Overview

TwoDay Coffee Roasters (twodaycoffee.co.uk) is a speciality coffee roaster in
Bristol, on a custom e-commerce storefront (not a hosted platform). The
founders first met fresh coffee roasting in Tokyo (living in Yoyogi-Koen)
after earlier years in New Orleans, and built the shop around roasting fresh
for the cup at home. The catalogue holds 9 saved coffees.

## Address

- 135 St Michael's Hill, Bristol, BS2 8BS — United Kingdom (shop open
  weekdays 9am–4pm).

## Philosophy & Quirks

- "It's all about the cup of coffee you make at home" — positioned for home
  (and office) brewing rather than cafe-only.
- Japanese coffee-culture origins; freshness-driven, with the shop open for
  walk-in coffee and home-blend advice.

## Scraping Quirks

- Custom e-commerce platform, not WooCommerce/Shopify/Squarespace.
- The module required a curl_cffi TLS fix (`impersonate="chrome"`) to get past
  the site's TLS fingerprinting — plain httpx requests are rejected.

## Sources

- https://twodaycoffee.co.uk
- https://twodaycoffee.co.uk/about-us/
- https://twodaycoffee.co.uk/shop