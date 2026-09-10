---
type: "Reference"
title: "Greytone Coffee — Roaster Profile"
description: "Bristol 'micro roastery' built around a minimalist 'Space for the Slow Moment' — neutral, harmonious roasting that refuses espresso-vs-filter categories."
---

# Greytone Coffee — Roaster Profile

## Overview

Greytone Coffee is a small roastery in Bristol, United Kingdom, describing
itself as "a micro roastery" that takes pride in "small-batch roasting,
precision, and showcasing the authentic character of every coffee origin".
The brand motto is "letting coffee speak for itself". The storefront is a
Wix shop at [greytonecoffee.co.uk](https://www.greytonecoffee.co.uk), and the
Dean Street Works site serves as both roastery and shop.

## Address

- Unit A, Dean Street Works, 13–19 Dean Street, Bristol, BS2 8SF — United
  Kingdom (open to the public Mon, Wed–Fri and weekends; closed Tuesdays)

## Schedules & Shipping

- Dispatch window is Wednesday through Friday each week; no dispatch on
  weekends or UK bank holidays.
- All orders ship via Royal Mail Tracked 48 with tracking emailed on
  dispatch.
- UK shipping only: orders under £40 cost £3.50; orders of £40 and over ship
  free. International enquiries are handled by email (info@greytonecoffee.co.uk).

## Philosophy & Quirks

- The brand story is titled "**A Space for the Slow Moment**" — the shop is
  designed as a "minimalist sanctuary" and "artistic, peaceful retreat",
  with every element chosen to foster calm.
- Roasting is deliberately anti-category: they "move away from rigid
  categories like espresso or filter" in favour of a "harmonious roasting
  style" that makes every roast versatile for any brew method.
- The house philosophy is neutrality — "we do not aim to impose a flavour,
  but rather to act as a quiet guide, revealing the inherent beauty already
  present in the harvest."

## Scraping Quirks

- **Sold-out products are skipped at the listing level**: on Wix, sold-out
  items show "Unavailable"/"Sold out"/"Out of stock" text in the
  `product-item-root` container; the scraper drops these *before* the
  coffee-URL filter so they never reach the catalogue.
- **AI-extraction soup narrowing**: Wix product pages embed everything inside
  `div[data-hook="product-page"]`; the scraper narrows the soup to that
  container before sending HTML to the AI extractor to cut token noise.

## Sources

- https://www.greytonecoffee.co.uk
- https://www.greytonecoffee.co.uk/our-philosophy
- https://www.greytonecoffee.co.uk/location
- https://www.greytonecoffee.co.uk/copy-of-return-policy (Delivery Information)
- https://www.greytonecoffee.co.uk/wholesale
