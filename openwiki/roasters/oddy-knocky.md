---
type: "Reference"
title: "Oddy Knocky Coffee — Roaster Profile"
description: "Bolton, Greater Manchester specialty roaster (Shopify) publishing a small rotating line of whole-bean coffees — House Blend, Slam Jam, The Notorious P.N.G., Faded — on the canonical oddyknockycoffee.co.uk storefront."
---

# Oddy Knocky Coffee — Roaster Profile

## Overview

Oddy Knocky Coffee (oddyknockycoffee.co.uk) is a specialty coffee roaster in
Bolton, Greater Manchester, publishing a small rotating line of whole-bean
coffees (blends plus single origins such as "House Blend", "Slam Jam", "The
Notorious P.N.G." and "Faded") on a Shopify storefront.

## Address

- Unit 16, Spring Street Business Park, Bolton, Greater Manchester BL3 6EH,
  United Kingdom.

## Scraping Quirks

- Domain correction: the canonical shop is oddyknockycoffee.co.uk (not
  oddyknocky.co.uk).
- oddyknockycoffee.co.uk's edge rejects curl_cffi's default TLS fingerprint, so
  the client is rebuilt with `impersonate="chrome"`.
- Shopify products.json from the curated `speciality-coffee` collection (wholesale
  duplicates, tote merch and the `coffee-club` subscription never enter the feed).
- e2e: 10 whole-bean coffees saved, no tasting-kit flags.

## Sources

- https://oddyknockycoffee.co.uk
- https://oddyknockycoffee.co.uk/pages/contact
- https://oddyknockycoffee.co.uk/collections/speciality-coffee