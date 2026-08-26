---
type: "Reference"
title: "Drip Roasters — Roaster Profile"
description: "Bern, Switzerland specialty roaster offering carefully sourced coffees in CHF, with canonical Shopify product URLs and a small-batch catalogue."
---

# Drip Roasters — Roaster Profile

## Overview

Drip Roasters is a specialty coffee roaster based in Bern, Switzerland (per the
roaster's site and scraper declaration). Its online shop is Shopify-based and
offers coffee in CHF. The site presents single-origin coffees and other roasted
coffee products; the catalogue is collected from its coffee collection.

## Address

- Bern, Switzerland — full roastery street address not published on site.

## Scraping Quirks

- The scraper reads the Shopify `coffee` collection and product JSON, then
  canonicalises collection URLs to `/products/<handle>`.
- It excludes non-bean products such as subscriptions, equipment, apparel,
  pods/capsules, drip bags, batch-brew products and gift items. This is a
  catalogue rule rather than a generic Shopify assumption.

## Sources

- https://driproasters.ch
- https://driproasters.ch/collections/coffee
