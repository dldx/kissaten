---
type: "Reference"
title: "Obra Coffee Roasters — Roaster Profile"
description: "Tiny East Sussex roastery founded by Patrick — named after the Spanish word for 'work' from his Cuban-American heritage, with a duck logo doodled by his 6-year-old daughter."
---

# Obra Coffee Roasters — Roaster Profile

## Overview

Obra Coffee Roasters is a small-batch specialty roaster based in East Sussex,
England (the site itself publishes no street address). Founder Patrick started
the project experimenting in his kitchen on a tiny manual roaster, giving beans
away to family and friends, and named it *Obra* — Spanish for "work", as in a
work of art or one's life's acts and deeds — in honour of his Cuban-American
heritage. The catalogue is deliberately tiny: at the time of writing just three
single origins (Butawa from Uganda via The Coffee Gardens, Damaris Medina Pink
Bourbon from Huila, Colombia, and La Bolsa from Guatemala), sold as 250g bags
roughly £11–£14. Storefront is Shopify at
[obracoffee.com](https://obracoffee.com), with subscriptions from £11.

## Address

- East Sussex, England, United Kingdom — full address not published on site.

## Schedules & Shipping

- A sitewide banner publishes the **latest roast date**, and the shop advises
  that all coffees are best brewed **7 to 10 days after roasting** — "check the
  date before applying hot water".
- No dispatch schedule, shipping rates or free-delivery threshold are published
  on the site; checkout supports GBP, EUR, USD, CAD and several other European
  currencies.

## Philosophy & Quirks

- The duck in the logo is a doodle Patrick found in his 6-year-old daughter's
  sketches — "it's my joy to share her work, and mine, with you".
- Product titles use a double-slash format, e.g. "Butawa // Uganda // 250g",
  packing producer, origin and size into the name.
- Roasting aims to "discover the fruit, the floral, and what makes every bean
  unique" — origin character over roast character.

## Scraping Quirks

- The scraper reads Shopify `products.json` from the two coffee collections
  (`/collections/espresso` and `/collections/filter`) and must **strip the
  collection segment from product URLs** — Obra's canonical product URLs are
  root-level (`/products/<slug>`), not `/collections/<name>/products/<slug>`.
- Coffee subscriptions (espresso/filter subscription products) are excluded by
  slug, alongside gift cards, capsules/pods and cold-brew cans.

## Sources

- https://obracoffee.com/
- https://obracoffee.com/pages/about
- https://obracoffee.com/pages/subscriptions
