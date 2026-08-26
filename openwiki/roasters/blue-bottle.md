---
type: "Reference"
title: "Blue Bottle Coffee — Roaster Profile"
description: "California-founded specialty brand represented here by its Japan online store, with blend and single-origin coffee alongside Japanese seasonal releases."
---

# Blue Bottle Coffee — Roaster Profile

## Overview

Blue Bottle Coffee is a California-founded specialty coffee brand with a Japan operation represented in Kissaten by the official Japanese Shopify store. The store sells blend and single-origin coffee, subscriptions, instant coffee, gifts and brewing equipment, alongside Japan-specific collaborations and seasonal products. This profile covers the Japanese storefront rather than assigning a café address to the roastery field.

## Address

- Japan — full roastery address not published on the consulted online-store pages.

## Schedules & Shipping

- The Japan online store advertises free shipping for orders of JPY 5,500 or more, with some exclusions. The consulted storefront does not publish a roast cadence or destination-specific shipping table beyond that Japan threshold.

## Scraping Quirks

- The scraper combines the `blend` and `single-origin` Shopify feeds, canonicalises product URLs to the direct `/products/<handle>` form, and forces translation to English. It excludes equipment and merchandise URL patterns plus the `s242` and `s006` Blend Selection tasting sets; it also drops extracted names containing `ground` or `selection`.

## Sources

- https://store.bluebottlecoffee.jp
- https://store.bluebottlecoffee.jp/pages/our-coffee
- https://store.bluebottlecoffee.jp/pages/sustainability
- https://store.bluebottlecoffee.jp/pages/user-guide
