---
type: "Reference"
title: "Echelon Coffee Roasters — Roaster Profile"
description: "Leeds-based roaster on Squarespace (Brine) at www.echeloncoffee.co.uk — the Spechelon/Espechelon espresso line plus filter single origins in 250g/1kg, with brewing equipment and subscriptions."
---

# Echelon Coffee Roasters — Roaster Profile

## Overview

Echelon Coffee Roasters is a Leeds-based speciality roaster on a Squarespace (Brine) storefront at www.echeloncoffee.co.uk. The /shop listing carries 7 coffee products — Colombia Demetrio Sanchez, Espechelon XII, Spechelon III, Kenya anaerobic / Kiamabara AB / Kimatu AB and Nicaragua Agua Sarca — in 250g/1kg sizes, alongside Hario/Kinto brewing equipment and subscription options.

## Address

- Unit 20, Penraevon Industrial Estate, Leeds LS7 2AW, England — United Kingdom

## Philosophy & Quirks

- Coffee names include the "Spechelon"/"Espechelon" espresso line (e.g. Spechelon III, ESPRECHELON XII).
- Sells both filter and espresso single origins, roasted to order, with a subscription service.

## Scraping Quirks

- Squarespace Brine theme — the /shop listing is server-rendered (`div.ProductList-item a[href*='/shop/']`); there is no `data-context` JSON (unlike Blue Hour).
- Product pages are `/shop/<slug>` (NOT `/shop/p/...`), so the required path pattern `/shop/` is used.
- Sold-out products are kept in the catalogue (needed for out-of-stock stock-update diffs).
- Brewing equipment (Hario V60, Kinto server) is excluded; subscriptions and gift cards live outside /shop and are excluded.

## Sources

- https://www.echeloncoffee.co.uk
- https://www.echeloncoffee.co.uk/shop