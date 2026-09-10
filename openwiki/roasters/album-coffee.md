---
type: "Reference"
title: "Album Coffee Roasters — Roaster Profile"
description: "A self-described 'nomadic' UK roastery that roasts short runs of vibrant, juicy coffees and pairs each release with commissioned cover artwork — SCA UK Roasting Champion 2016 & 2017."
---

# Album Coffee Roasters — Roaster Profile

## Overview

Album Coffee Roasters is a small United Kingdom roastery that "roast[s] short
runs of vibrant, juicy coffees and pair[s] them with interesting artworks" —
every coffee is released like an album track, with cover artwork credited to
design studios. The storefront is Shopify at
[albumcoffee.com](https://albumcoffee.com). Roaster Matthew
Robley-Siemonsma, a London-based coffee person, won the SCA UK Coffee Roasting
Championships in 2016 and 2017 (per their site). The current catalogue is tiny
by design: a handful of limited releases (e.g. Dopamine Grab, Vivarium,
Ancient Ambient, Lalesa) plus a monthly subscription that ships each newest
limited release.

## Address

- United Kingdom — Album is "still a somewhat 'nomadic' roastery" per their
  site; no fixed roastery address is published on the site.

## Sustainability

- Coffee bags are mono-material LDPE (no. 4 coded); customers are encouraged
  to remove the labels and return bags to supermarket carrier-bag recycling
  points, and to reuse the bags creatively.
- The site states they are still looking for a plastic-free alternative that
  protects the coffee.

## Roasting & Equipment

- No roasting machine is named on the site. The published roast style sits
  "somewhere between light and medium", aiming for "depth of sweetness,
  complex aromatics and juiciness while preserving a clean and transparent
  cup profile" — a sweet, developed filter roast and a lighter, juicier
  espresso.

## Schedules & Shipping

- Currently UK-only, on a 2–3 day tracked service, and **all shipping is
  free** (no minimum order threshold published).
- Orders ship in cardboard mailing boxes.
- The subscription ships the newest limited-release coffee once a month.

## Philosophy & Quirks

- Releases are named like music tracks — **Dopamine Grab**, **Vivarium**,
  **Ancient Ambient**, **Lalesa** — each with credited cover artwork (e.g.
  DR.ME Studio, elevatorteeth), echoing the "Album" concept. The homepage
  even carries volume-button graphics.
- Sourcing leans on unusual lots: "the best coffees might come from one small
  section of a farm, or a particular variety kept separate during harvest" —
  e.g. a co-fermentation with whole dragonfruit from Carlos Arcila in
  Quindío, Colombia.
- Whole bean only; the site points customers towards affordable grinders
  rather than selling them.

## Scraping Quirks

- The scraper's non-coffee exclusion list includes the slug fragments
  `-pack-`, `kit` and `set` — so any sampler/kit-style product would be
  silently dropped from the catalogue rather than flagged
  `is_tasting_kit`/`requires_review` for the review queue (see the
  [tasting-kit policy](../scrapers/scraping-system.md)). No such products
  were in the catalogue at the time of writing.

## Sources

- https://albumcoffee.com/
- https://albumcoffee.com/pages/about
- https://albumcoffee.com/pages/recycling
- https://albumcoffee.com/policies/shipping-policy