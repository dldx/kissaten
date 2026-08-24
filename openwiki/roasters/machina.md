---
type: "Reference"
title: "Machina Coffee — Roaster Profile"
description: "Edinburgh specialty roaster and equipment retailer (Machina Espresso, founded 2013) with a curated 24-bean catalogue of single origins, blends, decafs and experimental lots, roasted daily on two Probatone drum roasters."
---

# Machina Coffee — Roaster Profile

## Overview

Machina Coffee (Machina Espresso LTD) is an Edinburgh specialty roaster and
equipment retailer founded in 2013, on Shopify in GBP. The curated `coffee`
collection holds 24 beans — the complete published set: espresso blends
(Clockwork, Vox Pop, Index), single origins from Africa, South America, Mexico,
Nicaragua and Indonesia, plus low-caf, decaf and experimental lots. A large
home/commercial equipment range is not scraped. Canonical domain is
machina-coffee.com (.co.uk serves the same store).

## Address

- Unit 9 Peffermill Park, 25 Kings Haugh, Edinburgh, EH16 5UY — United Kingdom (roastery).
- 38 Marchmont Road, Edinburgh, EH9 1HX — United Kingdom (café).

## Sourcing & Transparency

- Works with three long-standing, trusted suppliers; an "ethical sourcing model"
  / "going beyond fair trade" — fair prices, no child labour, community
  investment (per their site).

## Roasting & Equipment

- Roasted daily in small batches on two traditional Probatone drum roasters
  (12 kg and 25 kg), with heavy QC investment (per their site).

## Schedules & Shipping

- Standard UK delivery within ~5 working days; collect from the Edinburgh café
  (per their customer-services page). No free-delivery minimum published.

## Scraping Quirks

- Shopify with Cloudflare (JSON works); only the curated `coffee` collection is
  scraped — 24 live beans, verified complete (all 13 bean sub-collections are
  subsets; `collections.json` over-counts unpublished — `espresso` claims 57 vs
  13 live, and one ghost product `kalingwe-uganda-espresso` 404s).
- Shopify Markets geo-conversion is active, so `country=GB` is pinned on every
  products.json fetch and currency is pinned to GBP.
- `body_html` is thin, so product pages are pruned to the Mucky-Puddle bean
  sections (~476 KB → ~37 KB).
- Espresso/Filter Collection Packs (4 × 250g samplers) are kit-flagged via the
  `collection-pack` token.
- Canonical URLs are machina-coffee.com/products/<handle>.

## Sources

- https://machina-coffee.com
- https://machina-coffee.com/collections/coffee
- https://machina-coffee.com/pages/contact
- https://machina-coffee.com/pages/about-our-coffee