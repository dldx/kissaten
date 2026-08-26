---
type: "Reference"
title: "Coffee County — Roaster Profile"
description: "Japanese specialty roaster with a coffee-bean shop spanning blends and single origins, alongside cafes in Fukuoka, Kurume, Tokyo and elsewhere."
---

# Coffee County — Roaster Profile

## Overview

Coffee County is a Japanese specialty coffee roaster whose online shop lists
coffee under BLEND and SINGLE ORIGIN categories. The company also operates
cafes in Fukuoka, Kurume and Tokyo. Its web shop is a GMO Shop-Pro storefront;
the product pages are Japanese and list bags in yen.

## Address

- Japan — full roastery address not published on the consulted site pages.

## Schedules & Shipping

- The online shop's Japanese shipping notice states that shipping within Japan
  is free for orders of at least 7,000 yen. It also lists domestic postal
  options; international shipping is not documented on the consulted pages.

## Scraping Quirks

- The scraper targets the `COFFEE BEANS` category (`cbid=1276755`) and walks
  its `?page=N` pagination. It excludes sold-out products by checking the
  product card, not the whole page. The shop uses EUC-JP; the scraper translates
  product pages to English for extraction.

## Sources

- https://coffeecounty.cc/
- https://shop.coffeecounty.cc/?mode=cate&cbid=1276755&csid=0
