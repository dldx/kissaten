---
type: "Reference"
title: "Humble Coffee — Roaster Profile"
description: "Durban specialty roaster and café on a Shopify storefront priced in ZAR — single origins, two blends and a decaf alongside a big catering menu."
---

# Humble Coffee — Roaster Profile

## Overview

Humble Coffee is a specialty coffee roaster and café based in Durban, KwaZulu-
Natal, South Africa, trading on a Shopify storefront priced in ZAR. The bean
line-up is compact: single origins from Colombia (Huila Select), Guatemala
(Finca Barillas), Ethiopia (Lalesa), Indonesia (Avatara) and Burundi (Kinama
Hill), plus a Humble House Blend, a Love Blend and an El Tucán Mexican decaf —
each with weight and grind-option variants. The same operation runs a large
catering business (breakfast/lunch platters, whole cakes, pastries) sold
through the same store, alongside merch, Nespresso-compatible pods and
MILKLAB alternative milks. Most narrative pages (About, FAQs, "The Story of
Big Rosie") are empty placeholders — the shop itself carries nearly all the
published information.

## Address

- 21a Churchill Road, Durban, KwaZulu-Natal, 4001, South Africa (per the
  store's Shopify contact-information policy page).

## Schedules & Shipping

- No roast/dispatch schedule or delivery rates are published on site; the
  "Returns and Shipping" page covers only a 14-day return policy (returns
  initiated via amy@humblecoffee.co.za, refunds within 10 business days).

## Philosophy & Quirks

- Bag labels state the coffee is "best enjoyed within 1 month of roast date"
  and should be recycled "with your plastic waste"; a ROAST DATE field is
  printed on every bag.
- Product pages label each coffee with roast level ("Light") and a "Best for"
  brew style (Filter/Espresso) alongside producer, process and altitude.
- Branding leans handwritten/homely ("Humble" scrawl logo, a "Book a table"
  widget for the café) — humble in name and presentation.

## Scraping Quirks

- The curated `collections/coffee` endpoint is the bean catalogue (9 products
  on capture); `collections/all` additionally carries the catering menu,
  gift cards, pods and merch.
- The Nespresso pod box is classified by Shopify as product_type "Coffee" and
  sits inside the coffee collection, so it must be excluded by the `pods`
  slug rather than by product-type filtering.
- Product URLs are canonicalised to the no-collection `/products/<handle>`
  form the live site serves, and store currency is pinned to ZAR against
  Shopify Markets geo-conversion.

## Sources

- https://www.humblecoffee.co.za
- https://www.humblecoffee.co.za/policies/contact-information
- https://www.humblecoffee.co.za/pages/returns-and-shipping
- https://www.humblecoffee.co.za/collections/coffee/products.json
- https://www.humblecoffee.co.za/products/lalesa-ethiopia (bag label: roast
  date / enjoy-within guidance)
