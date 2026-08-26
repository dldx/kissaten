---
type: "Reference"
title: "Chronic Coffee — Roaster Profile"
description: "Geneva-area Swiss roaster founded in 2017, combining daily small-batch roasting with organic/Fairtrade coffees, B Corp status and 1% for the Planet giving."
---

# Chronic Coffee — Roaster Profile

## Overview

Chronic Coffee is an independent Swiss specialty roaster founded in 2017 and
based in the Geneva area. Its Shopify shop offers seasonal, permanent,
decaffeinated and exceptional coffees plus brew bags, subscriptions and
equipment. Chronic describes its roasting as artisan, slow and designed for
everyday brewing methods rather than capsules.

## Address

- Roastery: Chemin de la Mousse 50B, 1225 Chêne-Bourg, Switzerland. The site
  presents this as the roastery pickup location; pickup is Monday–Friday,
  09:00–17:00. The Geneva store at Rue Argand 2 is a separate retail location.

## Sustainability

- Chronic identifies itself as B Corp, EcoEntreprise Excellence and a 1% for
  the Planet member. It says it donates 1% of revenue to WWF Switzerland and
  Terre des Hommes Switzerland, and works with Swiss social-integration
  programmes. Its coffees are presented as organic or Fairtrade certified,
  depending on the product.

## Sourcing & Transparency

- Chronic says it selects traceable coffees from committed producers and
  prioritises organic farming, ethics and long-term relationships. Product and
  brand pages describe origin, process and roast information, but the consulted
  pages publish no FOB, farm-gate or price-paid-to-producer figures.

## Roasting & Equipment

- Chronic describes hand roasting in small batches and a slow, gentle, precise
  process adapted to origin and brew method. Its official site shows a Loring
  roaster in a roasting image, but does not publish the model or capacity.

## Schedules & Shipping

- Chronic says it roasts daily and that coffee no older than 15 days ships from
  stock. Subscription delivery fees are waived from CHF 30; no general-store
  shipping threshold or destination rate table was visible on the consulted
  pages.

## Philosophy & Quirks

- The brand's “no capsules, no gimmicks” positioning is paired with coffee
  organised by use—filter, espresso, automatic machine and moka pot—rather
  than a single roast-level scale.

## Scraping Quirks

- The scraper scans `/collections/all/products.json` but accepts only products
  whose exact Shopify `product_type` is `Coffee beans ` (including the trailing
  space), then applies a second slug exclusion list. It fetches and caches
  product pages, narrows extraction to the main product section, and strips
  collection segments from canonical URLs.

## Sources

- https://chronic-coffee.co.uk
- https://chronic-coffee.co.uk/pages/about
- https://chronic-coffee.co.uk/pages/sustainability
