---
type: "Reference"
title: "S&W Roasting — Roaster Profile"
description: "US specialty roaster offering lighter single origins, roaster selections and blends through a Square Online shop."
---

# S&W Roasting — Roaster Profile

## Overview

S&W Roasting is a United States specialty roaster whose shop presents lighter
single-origin coffees, roaster selections and blends. Its registered store is
the Square Online site at swroasting.coffee. The reviewed official pages did
not publish a reliable founding story, equipment specification, sustainability
programme or producer-price data.

## Address

- United States — full roastery address not published on the reviewed site.

## Scraping Quirks

- The scraper uses three separate Square Online category URLs: lighter
  single-origin coffees, roaster selections and blends/medium roasts.
- Square's Cookiebot banner can block product rendering, and the site rejects
  bot user agents with 500 responses; the scraper therefore uses a browser-like
  header, Playwright, cookie dismissal and a wait for `/product/` links.
- On product pages it narrows the document to `div.product-detail-page` before
  AI extraction.

## Sources

- https://www.swroasting.coffee
- https://www.swroasting.coffee/shop/single-origin-coffees-lighter-roasts/2?page=1&limit=30&sort_by=category_order&sort_order=asc
- https://www.swroasting.coffee/shop/roasters-select/5?page=1&limit=30&sort_by=category_order&sort_order=asc
- https://www.swroasting.coffee/shop/blends-and-medium-roasts/3?page=1&limit=30&sort_by=category_order&sort_order=asc
