---
type: "Reference"
title: "Slow Coffee Roasters — Roaster Profile"
description: "Cambridge, New Zealand roaster releasing direct-sourced coffees weekly, with a fortnightly new-release rhythm and DHL Express international delivery."
---

# Slow Coffee Roasters — Roaster Profile

## Overview

Slow Coffee Roasters is a specialty roaster based in Cambridge, New Zealand,
with a Shopify storefront. The site describes a rotating range of single
origins, blends, espresso and filter coffees, alongside subscriptions and
brew equipment. It advertises a new release every fortnight and identifies
some current coffees as direct sourced.

## Address

- Cambridge, New Zealand — full roastery address not published on site.

## Sourcing & Transparency

- The storefront describes current releases as sourced direct and names
  producers, farms and processes on product pages. No producer price,
  FOB-per-kg figure or cost breakdown was found on the reviewed pages.

## Schedules & Shipping

- The site says the espresso programme is roasted weekly in Cambridge and
  advertises a new release every fortnight.
- The storefront advertises DHL Express worldwide delivery. For the UK it
  publishes NZ$-origin pricing converted for the selected region: £9 shipping
  in 2–5 days, duties and taxes included, with complimentary shipping over
  £90.
- At the time of review the site warned that orders would ship Monday 24
  August because of short staffing; this is a temporary notice, not a normal
  dispatch schedule.

## Scraping Quirks

- The scraper visits only the espresso and filter collection URLs and uses
  Playwright plus AI extraction for new products.
- On product pages it narrows the parsed document to the first
  `main > div.shopify-section` and removes `x-data` attributes before AI
  extraction.
- It filters equipment, subscriptions, gifts, merchandise, matcha, drip bags,
  Orea products and other named non-bean slugs.

## Sources

- https://slowcoffee.co.nz
- https://slowcoffee.co.nz/pages/about-us
- https://slowcoffee.co.nz/pages/coffee-production
- https://slowcoffee.co.nz/pages/shipping-timeframes
- https://slowcoffee.co.nz/pages/sustainability
