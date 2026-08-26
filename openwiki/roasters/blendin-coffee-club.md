---
type: "Reference"
title: "BlendIn Coffee Club — Roaster Profile"
description: "Sugar Land, Texas roaster founded by biochemist and 2024 US Brewers Cup Champion Weihong Zhang, pairing farm-traceable coffees with an intentionally welcoming coffee culture."
---

# BlendIn Coffee Club — Roaster Profile

## Overview

BlendIn Coffee Club is based in Sugar Land, Texas, and also operates an Allen Parkway cafe in Houston. Weihong Zhang came to the United States for a biochemistry PhD, founded BlendIn in 2017 after a formative Kenya coffee, and now designs the roast profiles. The menu is organised into Producers' Best, The Daily, and Collaborations; per their site, each coffee is traceable to a farm and often to a specific lot.

## Address

- 8410 US-90 ALT, Building B, Sugar Land, TX 77478 - United States
- 3201 Allen Parkway, Suite 170, Houston, TX 77019 - United States

## Sourcing & Transparency

- BlendIn says its Producers' Best coffees are sourced directly from farms and long-term producer relationships. It says every roasted coffee is traceable to a specific farm, often a specific lot, and selected at peak ripeness; no FOB or price-paid-to-producer figures are published on the pages checked.

## Schedules & Shipping

- Coffee is roasted to order in weekly batches Monday through Wednesday and shipped every Thursday. Orders placed after the Wednesday 12:00 PM Central cutoff move to the following Thursday. Typical transit is 2-5 business days via USPS or UPS, and US orders over USD 50 ship free.

## Philosophy & Quirks

- Zhang won the 2024 US Brewers Cup with a fully decaffeinated Typica and represented the United States at the World Brewers Cup. BlendIn's stated mission is to inspire appreciation of coffee through quality, inviting culture, service, and approachable education.

## Scraping Quirks

- The Shopify scraper uses `collections/coffee/products.json` but product metadata needed for extraction lives in the `bic-archive-detail` and `bic-pdp-origin` HTML blocks. It canonicalises collection URLs to `/products/<handle>` and limits page extraction to those information blocks. Its defensive exclusions cover subscriptions, gifts, merch, and equipment.

## Sources

- https://blendincoffeeclub.com/pages/about
- https://blendincoffeeclub.com/pages/coffee
- https://blendincoffeeclub.com/policies/shipping-policy
