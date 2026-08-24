---
type: "Reference"
title: "Groupwork Coffee Roasters — Roaster Profile"
description: "Newcastle (County Down, NI) roaster on Shopify built on a 'Better Shared' collaboration model — 8 coffees named by working relationship (PROJECT, FIELD TRIP, PARTNERSHIP, COMMUNITY, BALANCE), a house espresso and a decaf."
---

# Groupwork Coffee Roasters — Roaster Profile

## Overview

Groupwork Coffee Roasters is a roaster on a Shopify storefront at
groupworkcoffee.com, describing its model as "Better Shared". Its `coffee`
collection carries 8 products priced in GBP — collaboration-named single
origins such as FIELD TRIP Kanya Rwanda £14.00, PARTNERSHIP Los Milagros
Mexico £14.50, COMMUNITY Sierra Nevada Colombia £14.00 and BALANCE El Guayacan
Peru £14.50, plus the PROJECT house espresso £12.00, Abstract Finca Milan
£20.00, Las Esmeraldas and the Tumbaga decaf £15.00.

## Address

- Railway Street Café & Brew Bar, 2 Railway Street, Newcastle BT33 0AJ,
  County Down — United Kingdom (Northern Ireland; per the site's contact page).

## Schedules & Shipping

- Coffee orders placed before 12pm midday are dispatched the next working day
  (Mon–Fri) via DPD Tracked service as default.
- Free tracked shipping on all orders over £30 (within NI).

## Philosophy & Quirks

- "Better Shared" collaboration model — each coffee is named by its working
  relationship (PROJECT / FIELD TRIP / PARTNERSHIP / COMMUNITY / BALANCE).
- House espresso plus single origins and a decaf.

## Scraping Quirks

- The master `/collections/coffee` holds 9 raw products; the one subscription
  is excluded, leaving 8 in the catalogue. The `coffee-1` collection is an
  empty duplicate (0 products) and is ignored.
- Canonical product URLs are `/products/<handle>` (the collection segment is
  stripped).
- Currency is pinned to GBP, including removing the `Accept-Language` header
  so Shopify serves the base GBP market instead of a geo-localized presentment
  currency.

## Sources

- https://groupworkcoffee.com
- https://groupworkcoffee.com/collections/coffee