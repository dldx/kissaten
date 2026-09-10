---
type: "Reference"
title: "Carter Coffee — Roaster Profile"
description: "Edinburgh's new kids on the block — anaerobic-natural single origins, a rotating 'Bread & Butter' house blend, half-caff and sugarcane-decaf options, all small-batch roasted in Scotland."
---

# Carter Coffee — Roaster Profile

## Overview

Carter Coffee is a speciality coffee roaster based in Edinburgh, Scotland —
per third-party listings, "Edinburgh's new kids on the block", founded by
Danny and Sorley, whose roasting and brewing experience spans "from Australia
to Scotland". The site is a Shopify storefront at
[cartercoffee.uk](https://cartercoffee.uk). The range leans experimental:
anaerobic-natural single origins (Lalesa Ethiopia, Sipi Falls Uganda, La
Picona Nicaragua, Siracusa Colombia), a rotating seasonal house blend
(**Bread & Butter**), a half-caff blend (**Night Jam**) and a sugarcane-decaf
Colombia (**El Buho**). They also run a small coffee shop in Bonnington,
Edinburgh (open 7am–noon Wed–Fri, per the site banner); per local press it
soft-launched in 2026 at 4 Fyfe Lane.

## Address

- Edinburgh, Scotland — United Kingdom. The roastery address is not
  published on the site; the coffee shop operates in Bonnington, Edinburgh.

## Philosophy & Quirks

- "The best coffee is better shared" — a philosophy of craftsmanship,
  connection and relationships; the offer list is picked flavour-first with
  established farmers who value quality and innovation (per third-party
  listings).
- Playful naming throughout: **Bread & Butter** (self-described "the
  coffee-coffee" — "functional, sweet, chocolatey and versatile"), **Choccy
  Block**, **Night Jam**, **Carter Daily** subscription pack.
- Blends are explicitly seasonal — e.g. Bread & Butter's Brazil / Ethiopia /
  Uganda components rotate through the year.
- Site banner declares the rhythm of the business: "Cooking Monday &
  Tuesday | Packing all week".

## Scraping Quirks

- **Merch and subscription exclusions**: the scraper excludes the Carter
  cap, socks and t-shirt plus the "Carter Daily" subscription pack
  (`carter-x-platform-pack`) by full-handle slug, so only coffee enters the
  catalogue.
- **URL canonicalisation**: product URLs from `/collections/all/products.json`
  carry a `/collections/all` segment that the live site doesn't use; the
  scraper strips it to produce `/products/<handle>` URLs.

## Sources

- https://cartercoffee.uk/
- https://cartercoffee.uk/products/bread-butter-blend-ethiopia-brazil-colombia
- https://cartercoffee.uk/pages/contact
- https://dropbylocal.com/shop/coffee/carter-coffee
- https://www.deadlinenews.co.uk/2026/04/08/new-coffee-shop-offering-distinctive-blends-to-open-in-bonnington/