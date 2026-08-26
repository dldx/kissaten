---
type: "Reference"
title: "Mad Heads Coffee — Roaster Profile"
description: "Kyiv speciality roaster whose catalogue is served from a three-page Ukrainian coffee shop and whose orders are dispatched every day."
---

# Mad Heads Coffee — Roaster Profile

## Overview

Mad Heads Coffee is a speciality coffee roaster based in Kyiv, Ukraine. Its English storefront presents a catalogue of coffee and describes the business as Madheads Coffee roasters. The company’s published contact page identifies its Kyiv premises at 69 Kyrylivska Street.

## Address

- 69 Kyrylivska Street, Kyiv 02000, Ukraine — listed by the roaster as its Madheads Coffee roasters location.

## Schedules & Shipping

- The roaster says it processes and ships orders every day. Orders placed before 16:00 are dispatched the same day; Kyiv delivery may be same-day, while delivery time for Ukraine and international shipments depends on the carrier. Delivery within Ukraine is stated to be at the roaster’s expense.

## Philosophy & Quirks

- The site’s published payment and shipping page offers cash on delivery and bank transfer, alongside card payment, rather than presenting a free-delivery order threshold.

## Scraping Quirks

- The registry key is `mad-heads-coffee`. The scraper hard-codes three English catalogue URLs (`/en/catalog/c=3&p=1` through `p=3`), uses Playwright and AI extraction for new products, and narrows fetched product pages to `div.all-cont-section`. It currently has no URL exclusions, so catalogue changes should be checked for non-coffee products.

## Sources

- https://madheadscoffee.com/en/about
- https://madheadscoffee.com/en/contacts
- https://madheadscoffee.com/en/dostavka-i-oplata
