---
type: "Reference"
title: "Gold Box Roastery — Roaster Profile"
description: "Specialty coffee roaster with UK (Blaydon, Newcastle) and Dubai operations; the reviewed goldboxroastery.com storefront is the Dubai (AED) shop — competition-series geishas, microlots and house blends, roasted on a Probat, with a UK Brewers Cup Champion on the team."
---

# Gold Box Roastery — Roaster Profile

## Overview

Gold Box Roastery (Gold Box Coffee Roasters) is a specialty coffee roaster
with operations in the UK (Blaydon, Newcastle) and Dubai. The reviewed
Shopify storefront at goldboxroastery.com operates from Dubai and sells in
AED. Its curated `coffee` collection has 41 products — competition lots and
geishas (CGLE Napoléon Geisha Competition Series at 175–380 Dhs, Lola/Miya/Lyla
Panama Geishas, Yemen Mocha Mountain), microlots and experimental lots
(Colombia Mango Bliss, Frozen Passion Fruit, Watermelon Rush, Kenya Anaerobic,
China Mystic Yunnan) and house blends (Bond Street Espresso Blend, Dark
Sugars), plus Discovery and Experimental Taster Boxes. It also sells green
coffee, tea, equipment and used equipment. Its focus is specialty, direct
trade, microlots and competition lots, roasted on a Probat in its coffee lab.

## Address

- Warehouse #7, Building: SMARK 3, Umm Suqeim Rd. East, near Mall of the
  Emirates, Al Quoz Industrial Third, PO Box 214919, Dubai — United Arab
  Emirates (this storefront, per the site's location widget).
- 6–8 Vance Court, Transbritannia Enterprise Park, Blaydon, Newcastle upon
  Tyne NE21 5NH — United Kingdom (claimed UK HQ/roastery per their site).

## Sourcing & Transparency

- The site claims a specialty / direct-trade / microlot / competition-lot
  focus, with origin–altitude–process detail on products (per their site).
- No FOB / farm-gate price-transparency figures are published.

## Philosophy & Quirks

- Competition-grade coffees — geishas, anaerobic lots and frozen-fruit
  experimental lots; motto "Roasted with Passion. Perfected by Science."
- UK Brewers Cup connection — Luca Croce, UK Brewers Cup Champion 2022–23 and
  4th at the World Brewers Cup, based at the Dubai (Al Barsha) branch; founder
  Barbara Croce.
- Arabic Gahwa is among the coffee products.
- Discovery and Experimental Taster Boxes are flagged as tasting kits.

## Scraping Quirks

- Shopify UAE/AED storefront (currency AED, "Dhs." money format — NOT GBP;
  this storefront is the Dubai shop).
- Curated `/collections/coffee` (41 products).
- Canonical `/products/<handle>` (collection segment stripped).
- The Discovery Taster Box and Experimental Taster Box are tasting kits — the
  base `"discovery"` exclusion pattern would wrongly drop
  `discovery-taster-box`, so the scraper overrides
  `_get_excluded_url_patterns()` to remove `"discovery"` and adds
  `"taster-box"` to the tasting-kit patterns; both boxes are flagged
  `is_tasting_kit` / `requires_review` into the review queue.

## Sources

- https://goldboxroastery.com
- https://goldboxroastery.com/collections/coffee
- https://goldboxroastery.com/pages/uk-location
- https://goldboxroastery.com/pages/coffee-roasters
