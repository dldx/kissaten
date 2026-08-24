---
type: "Reference"
title: "Inverness Coffee Roasting — Roaster Profile"
description: "Inverness (Scottish Highlands) roastery on Shopify at invernesscoffeeroasting.co.uk roasting fresh every day for retail and wholesale customers across the Highlands, with a 19-product coffee collection (Sierra Nevada, Highland Roast, Monsoon Malabar, Coffee of the Month)."
---

# Inverness Coffee Roasting — Roaster Profile

## Overview

Inverness Coffee Roasting Co. is a Scottish Highlands roastery in Inverness on
a Shopify storefront at invernesscoffeeroasting.co.uk. It roasts coffee every
day and dispatches directly from the roastery, supplying retail plus local
restaurants, delis, cafés and hotels across the Highlands. The curated coffee
collection holds 19 products — 17 whole-bean coffees after excluding two
capsule lines — including Sierra Nevada (Colombia), Highland Roast, Monsoon
Malabar and a rotating Coffee of the Month.

## Address

- Shop: 15 Chapel Street, Inverness IV1 1NA; roastery: 2 Cromwell Industrial
  Buildings, Lotland Street, Inverness IV1 1YL — United Kingdom (Scotland).

## Schedules & Shipping

- Roasted every day in small batches; orders typically dispatched within ~2
  business days (per their shipping policy).
- UK-only shipping at a flat £3.50; free local pickup (click & collect) from
  the Chapel Street shop.

## Philosophy & Quirks

- Team identity built around owner "Kevin the Coffee Baron" and the rest of
  "Team Bean", each with a favourite coffee and brew method on the about page.
- Offers barista training, custom house-blend development ("your own unique
  roast") and commercial espresso machine sales (La Spaziale / Ibertial
  distributor) alongside the beans.

## Scraping Quirks

- Shopify; curated `coffee` collection holds 19 published products while
  `collections.json` over-counts at 53 (unpublished items).
- Page scraping required: products.json `body_html` is prose-only; the
  structured detail (Region, Altitude, Harvest, Varietal, Milling, Cupping
  Notes, Strength) lives only in the rendered `div.extra-details`, and the
  soup is pruned to `div.product__info-wrapper`.
- Two capsule products excluded: `strike-the-light-capsules` (base pattern
  catches it) and `be-gone-yawn` (explicit slug — its handle lacks
  "capsules").
- Canonical product URLs are `/products/<handle>` (collection segment
  stripped).

## Sources

- https://invernesscoffeeroasting.co.uk
- https://invernesscoffeeroasting.co.uk/pages/about-us
- https://invernesscoffeeroasting.co.uk/pages/contact
- https://invernesscoffeeroasting.co.uk/policies/shipping-policy
