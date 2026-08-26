---
type: "Reference"
title: "Proud Mary Coffee — Roaster Profile"
description: "Proud Mary’s US operation, with a Portland roastery, Portland and Austin cafés, and a wide range from everyday blends to limited high-end releases."
---

# Proud Mary Coffee — Roaster Profile

## Overview

Proud Mary Coffee USA is a specialty coffee business with a Shopify shop, a Portland roastery, and cafés in Portland and Austin. The online range is divided into Mild, Curious, Wild and Deluxe coffees, alongside blends, subscriptions, instant coffee and merchandise. The storefront also carries limited coffees named for producers and farms, including current releases from Honduras, Mexico, Panama, Nicaragua, Guatemala and Ethiopia.

## Address

- 3961 N Williams Ave, Portland, OR — United States (roastery address published in the site footer).

## Schedules & Shipping

- Subscription products are marked “Free Shipping” in the storefront. The fetched pages did not publish a general free-delivery minimum, roast cadence, dispatch days, or destination-specific rate table.

## Scraping Quirks

- The scraper uses the `/collections/all-coffee` catalogue and custom product-link selectors, then uses Playwright for full AI extraction.
- URL filtering excludes subscriptions, bundles, gift products, instant coffee and the `picnmix`/`pic-n-mix` products, so the online catalogue is intentionally narrower than the storefront.

## Sources

- https://proudmarycoffee.com
- https://proudmarycoffee.com/collections/all-coffee
- https://proudmarycoffee.com/pages/shipping
