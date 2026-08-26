---
type: "Reference"
title: "Casa Coffee Roasters — Roaster Profile"
description: "Independent Yorkshire specialty roaster (rebranded from Casa Espresso) in Shipley, West Yorkshire on a WooCommerce storefront, selling core espresso blends plus rotating single-origin discovery coffees and curated sample packs."
---

# Casa Coffee Roasters — Roaster Profile

## Overview

Casa Coffee Roasters (casacoffeeroasters.co.uk) is an independent Yorkshire
specialty roaster based in the Bradford/Shipley area, West Yorkshire,
rebranded from the former Casa Espresso / Casa Coffee operation (the old
casacoffee.co.uk domain is parked). It runs on a WordPress + WooCommerce
storefront in GBP. The catalogue is a rotating set of core espresso blends
(Charlestown Espresso, Union Espresso) and single-origin discovery coffees,
plus curated sample packs for both ranges.

## Address

- Unit 1, Briar Rhydding House, Otley Road, Shipley, West Yorkshire, BD17 7JW —
  United Kingdom.

## Schedules & Shipping

- Free UK shipping on orders over £30.
- Office hours Mon–Fri 9.00am–5.30pm; contact 01274 595841 or
  hello@casacoffeeroasters.co.uk.

## Scraping Quirks

- Rebrand correction: casacoffee.co.uk → casacoffeeroasters.co.uk (old domain
  parked).
- WooCommerce storefront scraped from the `/coffee/` product category
  (authoritative in-stock list) with WooCommerce `outofstock` card-class
  skipping.
- Two curated sample packs (Sample Pack Core, Sample Pack Discovery Range) are
  tasting kits: they must flow through the review queue
  (`is_tasting_kit`/`requires_review`), never excluded — the generic
  `"discovery"` exclusion is dropped for this roaster so the Discovery
  single-origin range and its sample pack land in the catalogue.
- The `lucky-dip` product persistently fails AI extraction and is not saved
  (11 of 12 whole-bean products saved: 9 beans + 2 kits).

## Sources

- https://casacoffeeroasters.co.uk
- https://casacoffeeroasters.co.uk/coffee/
- https://casacoffeeroasters.co.uk/contact/