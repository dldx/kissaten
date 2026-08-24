---
type: "Reference"
title: "Fortitude Coffee Roasters — Roaster Profile"
description: "Edinburgh specialty roaster (est. 2014) on Squarespace at fortitudecoffee.com with 10 coffees — Rwanda, Kenya, Colombia and Gesha single origins plus subscriptions — in 250g/1kg, GBP."
---

# Fortitude Coffee Roasters — Roaster Profile

## Overview

Fortitude is an Edinburgh specialty roaster established in 2014, on a Squarespace storefront at fortitudecoffee.com. The /coffee collection carries 10 coffees — Blend V.2, Shyira washed and natural Rwanda, Gatubu AA Kenya, El Carmen sugarcane decaf Colombia, Corozal, Finca Maracay Gesha, Meridiano Typica Ecuador, Finca Anaya, Morales Gesha Peru — roughly £10.50–£23.00 in 250g/1kg, GBP. Subscriptions are offered at /start.

## Address

- 66 Hamilton Place, Edinburgh, Scotland EH3 5AZ — United Kingdom (roastery + cafés; also 4 Abbey Mount EH8 8EJ)

## Philosophy & Quirks

- Established 2014; roastery plus two Edinburgh cafés.
- Product pages carry rich origin / producer / variety / process / altitude data per coffee.

## Scraping Quirks

- Squarespace — product pages are at `/webshop/p/<slug>` (the listing is a 7.1 summary gallery, not a Brine ProductList).
- The bare domain can time out from some clients — always use `www` with a browser UA and retries.
- Sold-out products (Finca Maracay, Finca Anaya) are kept in the catalogue for out-of-stock diffs.
- Screenshots hit a networkidle timeout → HTML-only fallback (0 errors). Currency pinned to GBP.

## Sources

- https://www.fortitudecoffee.com
- https://www.fortitudecoffee.com/coffee