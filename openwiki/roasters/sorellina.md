---
type: "Reference"
title: "Sorellina Coffee — Roaster Profile"
description: "Edmonton roaster with a deliberately tiny, terroir-first catalogue — single-farm lots from Ecuador, Panama and Colombia, plus a rare 'Brewers Series' for competition-size micro lots."
---

# Sorellina Coffee — Roaster Profile

## Overview

Sorellina is a Canadian specialty coffee roaster based in Edmonton, Alberta, selling through a Shopify storefront at sorellina.ca. The catalogue is intentionally small — typically fewer than ten coffees at a time, all single-farm lots (recently Ecuador, Panama, Guatemala and Colombia) — and is organised into three named tiers per their site: "Tales of Terroir" (pure expression of the land), "The Art of the Grower" (producer-driven agronomical choices and low-intervention processing) and "Futures of Processing" (innovation/controlled-fermentation lots). A fourth line, the "Brewers Series" (80–150 g packs of competition lots, rare varietals and ultra-small lots), is offered alongside. An instant coffee ("Sorellina Instant") rounds out the range. Founding year and founder names are not published on the site's rendered pages.

## Address

- Edmonton, Alberta, Canada (per their site — they deliver within "Edmonton's city limits, St. Albert, and Sherwood Park"; full street address not published on site).

## Schedules & Shipping

- Roasting cadence: roasting on Wednesdays; orders shipped Thursdays and Fridays. Order deadline for the Wednesday roast is Tuesday 11:59 PM (GMT-6); later orders roll to the next roast day (per their site).
- They recommend resting the coffee 2–3 weeks after roast before brewing (per their site).
- Free local delivery within Edmonton, St. Albert and Sherwood Park (Thursdays and Fridays) on orders of $25 CAD or more; orders under $25 carry a $5 CAD delivery fee, with a $5 CAD redelivery fee after two failed attempts (per their site).
- Shipping beyond the local zone is offered across Canada, USA, Central/South America, Europe, Asia and Australia/Oceania (per-region rates are presented in tabs on their shipping page that do not render headlessly; amounts not verified).

## Philosophy & Quirks

- The whole range is framed as storytelling: each product page presents a "PEOPLE, PLACE, PROCESS" spec table (producer, origin, farm, soil type, altitude, varietal, process) plus a "SENSORY" table splitting the cup into aroma, flavour and tactile rows — a structure unusual among Shopify roasters.
- Product titles are frequently re-purposed: the shop sells a "Madman Vol.2 – Flower Bomb" under a duplicate-handle product, and bag art is loud, holographic and punk-styled — an aesthetic that contrasts with the orthodox single-origin content.
- Whistle-stop product handles (e.g. `el-volcancito-pache-catuai-washed-guatemala` for a coffee titled "Willian Cano Navas – Guatemala") mean handles often describe a *previous* product — the store reuses handles by appending `-copy` instead of creating new ones.

## Scraping Quirks

- The Shopify `products.json` payload carries an **empty `body_html`** — all bean detail (producer, farm, altitude, varietal, process, tasting notes) lives only in the on-page spec tables, so the scraper must run in page-scraping mode with the soup pruned to the main product section.
- The curated collection is `/collections/allcoffee` (NOT `/collections/all`, which mixes in a Ceado grinder and Origami brew ware); note also that `/collections/beans` contains only a gift card.
- The same underlying coffee can appear under duplicate `-copy` handles (e.g. `finca-la-josefina-ecuador-typica-washed` and `finca-la-josefina-ecuador-typica-washed-copy` are different coffees — the second is "Madman Vol.2 – Flower Bomb"), so handle-based dedup assumptions can mislead.
- The store runs Shopify Markets with geo-converted prices (footer country selector spans GBP/EUR/USD markets); the scraper pins `store_currency = "CAD"` so datacenter-IP fetches cannot stamp converted prices onto beans.
- No tasting-kit/sampler products were present at scraper-creation time; there are no deliberate exclusions beyond the gift card and equipment slugs.

## Sources

- https://sorellina.ca/
- https://sorellina.ca/pages/shipping
- https://sorellina.ca/pages/about-the-coffee
- https://sorellina.ca/products/finca-la-josefina-ecuador-typica-washed
- https://sorellina.ca/collections/allcoffee/products.json
