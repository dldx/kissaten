---
type: "Reference"
title: "The Source Coffee Roasters — Roaster Profile"
description: "Edinburgh specialty coffee company with a coffee bar at 4 Spittal Street and an electric roaster in Livingston, selling whole-bean coffees from a curated Shopify collection."
---

# The Source Coffee Roasters — Roaster Profile

## Overview

The Source Coffee Roasters (thesourcecoffee.co.uk) is an Edinburgh specialty
coffee company with a coffee bar at 4 Spittal Street, Edinburgh, and a roastery
in Livingston — its wholesale page describes each batch as "small, intentional,
and roasted on our electric roaster in Livingston". Whole-bean single origins
and blends are sold from a curated `/collections/coffee` Shopify collection,
priced in GBP.

## Address

- Roastery in Livingston, West Lothian, United Kingdom — full roastery street
  address not published on site. The coffee bar is at 4 Spittal Street,
  Edinburgh, EH3 9DX.

## Scraping Quirks

- Shopify JSON-only from the curated `/collections/coffee` collection; a strict
  Shopify `product_type == "beans"` include-filter reproduces the whole-bean
  set (equipment, merchandise and subscriptions live elsewhere).
- Canonical product pages are the no-collection form; the collection segment
  is stripped.
- e2e: 9 saved, 0 kits.

## Sources

- https://thesourcecoffee.co.uk
- https://thesourcecoffee.co.uk/pages/contact
- https://thesourcecoffee.co.uk/pages/wholesale