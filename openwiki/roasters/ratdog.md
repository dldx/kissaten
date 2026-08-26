---
type: "Reference"
title: "Ratdog Speciality Coffee Roaster — Roaster Profile"
description: "UK micro-lot speciality coffee roaster on Shopify specialising in rare and exotic single-origin Geisha lots (Janson, La Esmeralda, Guji) plus archived sold-out beans, with free UK shipping over £30 and a premium Geisha blind-box sample kit in the review queue."
---

# Ratdog Speciality Coffee Roaster — Roaster Profile

## Overview

Ratdog Speciality Coffee Roaster (ratdogspecialitycoffeeroaster.com) is a UK
micro-lot speciality coffee roaster on Shopify priced in GBP. It describes
itself as a "micro-lot speciality roaster" focused on thoughtful roasting and
careful sourcing, with every coffee personally selected and roasted in small
batches. Its curated whole-bean catalogue of ~16 coffees leans on rare and
exotic single-origin Geisha lots (Janson, Elida, La Esmeralda, Guji) sourced
from celebrated farms across Panama, Colombia, Ethiopia, Honduras, Kenya and
Costa Rica, plus previously sold-out archived beans.

## Address

- Full street address not published on site — United Kingdom (site does not
  state a town or region).

## Sourcing & Transparency

- Per their site: every coffee is "personally selected" and roasted in small
  batches with a focus on "thoughtful roasting and careful sourcing".
- Catalogue specialises in rare/exotic single-origin lots from celebrated
  farms across Panama, Colombia, Ethiopia, Honduras, Kenya and Costa Rica
  (no price-paid-to-producer figures published).

## Schedules & Shipping

- Free UK shipping on orders over £30 (homepage / banner).

## Scraping Quirks

- Old domain `ratdogcoffee.co.uk` is DNS-dead; canonical shop is now
  `ratdogspecialitycoffeeroaster.com` (www redirects to the apex).
- The whole-bean catalogue is union of three nav collections (single-origin,
  rare-exotic, archived sold-out beans) mirroring the site's own menu; the
  rare-exotic collection is a strict subset of single-origin and dedups to
  canonical `/products/<handle>` URLs.
- Many products are limited-release carries with "Last bag, roasted …" dates
  baked into the product titles, and titles also carry per-bag roast dates.
- One product (the premium 15 g Geisha blind-box sample) is flagged
  `is_tasting_kit` / `requires_review` and flows through the admin review
  queue rather than being excluded or shown publicly.

## Sources

- https://ratdogspecialitycoffeeroaster.com
- https://ratdogspecialitycoffeeroaster.com/pages/contact
- https://ratdogspecialitycoffeeroaster.com/policies/shipping-policy