---
type: "Reference"
title: "Quaffee — Roaster Profile"
description: "Cape Town roaster since 2006 at Buitenverwachting, roasting to order under a frog banner, publishing FOB transparency via the Transparency.coffee pledge and selling green coffee to home roasters."
---

# Quaffee

## Overview

Quaffee is a Cape Town, South Africa roastery born from "a two decade long quest" for
fine quality coffee, roasting since 2006 with a philosophy of sourcing fine coffees
and roasting them fresh to order. The frog is the company symbol ("why the frog?") and
a constant reminder of that quest. Alongside roasted and green coffee it sells brewing
gear (grinders, manual brew, espresso machines), services (rentals, wholesale supply,
repairs, informal coffee tastings) and a coffee-beans subscription. The storefront is
a WordPress/WooCommerce shop whose archive is `/offerings/`; the company also tracks
and publishes the cups its clients have brewed (over 13.6 million since February 2007).

## Address

- Quaffee at Buitenverwachting, Klein Constantia Rd, Constantia, Cape Town, 7800, South Africa

## Sustainability

Per their delivery policy, Quaffee aims to use the delivery method with the lowest
carbon footprint available, accepting small delays to reduce emissions. The site also
publishes an environmental policy under "Reduce, Reuse, Recycle".

## Sourcing & Transparency

Since a June 2020 Transparency.coffee pledge, Quaffee publishes transparency
information (including FOB prices for coffees they can trace to source) for all its
coffees on their information pages; for its FYE2020/FYE2021 purchases it published
per-coffee transparency reports on site, classing any coffee with a traceable FOB
price as transparent. Their budget line (3-star and below) is the bulk of the
non-transparent share, chosen on taste but driven by price.

## Schedules & Shipping

Coffee is roasted to order. Orders for next-day (Greater Cape Town) delivery close at
15:30; delivery days per area are tabulated on the delivery page (e.g. Cape Town
Thu 8am–Fri 1pm orders → Monday). Outside their own delivery area they use FastWay or
The Courier Guy couriers, or Pargo depot collection; no deliveries outside South
Africa. Free delivery for: collection at Buitenverwachting, street addresses in
postal code 7806, orders above R500 to Cape Town and surrounds, above R550 to Gauteng,
Durban and other major regions, and above R1,000 to all other South African centres.

## Philosophy & Quirks

The frog symbolises the quest for quality and keeps the company honest about what it
stands for; the site carries a "Proudly South African / BEE" page and a quirky public
counter of client-brewed cups.

## Scraping Quirks

- **quaffee.com vs quaffee.co.za**: `https://www.quaffee.com` 301-redirects to
  `https://quaffee.co.za`, which is the canonical, actively maintained shop.
- The WooCommerce shop archive is `/offerings/` with ~198 products, the majority
  gear/machines; the scraper targets the `product-category/coffee/` and
  `product-category/green-coffee/` archives instead. Green (unroasted) beans for home
  roasters are a deliberate part of the catalogue.
- The `coffee-beans-subscription` product and the "coffee tasting experience" service
  are excluded; curated tasting kits, if listed, flow through the review queue
  (`is_tasting_kit` / `requires_review`).

## Sources

- https://quaffee.co.za/ (home)
- https://quaffee.co.za/about-us/
- https://quaffee.co.za/quaffee-home/quaffee/contact/
- https://quaffee.co.za/quaffee-home/quaffee/delivery-return-policy/
- https://quaffee.co.za/coffee-transparency/
- https://quaffee.co.za/product-category/coffee/ (incl. page 2)
- https://quaffee.co.za/product-category/green-coffee/
