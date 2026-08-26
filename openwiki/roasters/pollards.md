---
type: "Reference"
title: "Pollards Coffee — Roaster Profile"
description: "Sheffield roastery and shop at 627 Ecclesall Road on Shopify, with an African Selection tasting kit run through the review queue and a range of blends and single origins."
---

# Pollards Coffee — Roaster Profile

## Overview

Pollards Coffee (pollardscoffee.co.uk) is a Sheffield coffee roaster and shop
based at 627 Ecclesall Road, run largely solo (the site notes "we often work
alone in the shop"). It sells blends and single origins from a Shopify
storefront in GBP, alongside a dedicated "African Selection" tasting kit. The
catalogue holds 22 whole-bean coffees plus the kit; a further eight blends
without product images were dropped by the base data gate.

## Address

- 627 Ecclesall Road, Sheffield, South Yorkshire, S11 8PT — United Kingdom
  (published on the contact page).

## Scraping Quirks

- The "African Selection" is a tasting-kit product: it must flow through the
  review queue (`is_tasting_kit` / `requires_review`), never excluded.
- Eight blend products with no product images were dropped by the base data
  gate rather than saved.
- Domain correction: the live storefront is pollardscoffee.co.uk (the checklist
  row referenced pollards.com).

## Sources

- https://pollardscoffee.co.uk
- https://pollardscoffee.co.uk/collections/all
- https://pollardscoffee.co.uk/pages/contact-us