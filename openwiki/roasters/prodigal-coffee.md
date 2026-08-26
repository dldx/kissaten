---
type: "Reference"
title: "Prodigal Coffee — Roaster Profile"
description: "US specialty roaster offering highly detailed single-origin releases, weekly Monday roasting, espresso blends, green coffee and a Taste of Prodigal sampler."
---

# Prodigal Coffee — Roaster Profile

## Overview

Prodigal Coffee is a United States specialty roaster selling single origins, blends, green coffee, brewing goods and subscriptions through a Shopify storefront. The current catalogue presents coffees from origins including Kenya, Colombia, Ethiopia and Honduras, alongside espresso blends and the “Taste of Prodigal” sampler. The site features Scott Rao and Mark Benedetto as the people behind the business.

## Address

- United States — full roastery address not published on site.

## Schedules & Shipping

- The storefront says coffees are roasted weekly on Mondays. Orders containing an upcoming roast queue for that roast date; orders made only of green coffee, goods, or roasted coffees from prior roast dates ship by the next business day. The site separately warns West Asia customers to check local shipping restrictions; a complete fetched rate table was not available.

## Philosophy & Quirks

- The site explicitly advises that its light roasts improve with several weeks of rest and lets customers choose an upcoming roast or a prior roast date.

## Scraping Quirks

- The scraper reads the `roasted-coffee` collection and normalises collection product URLs to canonical `/products/<handle>` URLs.
- Its exclusion list removes subscriptions, gift products, wholesale, equipment and merchandise, but the live catalogue also contains the “Taste of Prodigal” sampler; it is not excluded by the scraper and should remain available for the tasting-kit review pipeline.

## Sources

- https://getprodigal.com
- https://getprodigal.com/collections/roasted-coffee
- https://getprodigal.com/pages/shipping-information
