---
type: "Reference"
title: "The Roasting Project — Roaster Profile"
description: "Fife (Kirkcaldy) roastery that began roasting on a Diedrich in a Burntisland coffee house in 2018 and now runs a purpose-built Kirkcaldy roastery; WooCommerce store of blends, single origins and brew gear."
---

# The Roasting Project — Roaster Profile

## Overview

The Roasting Project (www.theroastingproject.co.uk) is a Fife roastery based
in Kirkcaldy. It began roasting on a Diedrich in a humble Burntisland coffee
house in 2018 and has since expanded into a purpose-built roastery in Kirkcaldy
(per its About page). The WooCommerce storefront sells small-batch whole-bean
blends and single origins from `/buy-coffee/`, alongside a large "kit"
category of grinding/brewing equipment and coffee-subscription options, priced
in GBP.

## Address

- 5 Oswald Road, Kirkcaldy, Fife, KY1 3JE, United Kingdom (roastery address).

## Roasting & Equipment

- Roasting began on a Diedrich in a Burntisland coffee house in 2018; the
  roastery is now purpose-built in Kirkcaldy (per the About page).

## Scraping Quirks

- WooCommerce public Store API discovery (lost-barn / santu pattern); sold-out
  detection via the API `is_in_stock` flag; only the `coffee` category is
  kept, dropping the `kit` (equipment) and `subscriptions` categories plus
  subscription-named products.
- The non-`www` host 301-redirects to `www`; per-product AI extraction of
  JSON-LD-annotated pages.
- No samplers / tasting kits in the current catalogue — e2e: 15 saved, 0 kits.

## Sources

- https://www.theroastingproject.co.uk
- https://www.theroastingproject.co.uk/about/
- https://www.theroastingproject.co.uk/buy-coffee/