---
type: "Reference"
title: "Ithaka Coffee — Roaster Profile"
description: "Birmingham roastery being built by World Barista Champion Dale Harris — named after Cavafy's poem 'Ithaka', UN Sustainable Development Goals listed per coffee, shade-tree reforestation at Los Romerillos and a 'small is beautiful' values-over-growth ethos."
---

# Ithaka Coffee — Roaster Profile

## Overview

Ithaka is a Birmingham coffee roastery "being built by World Barista Champion
(2018), Dale Harris", alongside co-founder Alex Scott (per their site). It
deliberately "moves slowly" — the about page states "We'll never be the biggest
roastery, but we can be one that makes a fresh positive impact within our
community." The Shopify storefront sells single origins from Ethiopia,
Nicaragua, El Salvador, Bolivia, Mexico, Rwanda and Ecuador, and the roastery
doubles as a tasting bar under the railway arches next to the Custard Factory
(open Mon–Sat, 9am–4pm).

## Address

- 21 Gibb Street, Deritend, Birmingham B9 4BF — United Kingdom (the tasting
  bar "marks the front of the roastery"; store-pickup details on product pages
  list the same site as B9 4AR)

## Sustainability

- Each coffee is tagged with **UN Sustainable Development Goal icons**, backed
  by a journal post explaining the specific producer-side work behind them
  ("The icons you'll find on our website don't represent what we've done. They
  represent work that began long before a coffee ever reached our roastery").
- **Los Romerillos (Ecuador)**: part of the price paid for their coffee funds
  on-farm reforestation — 119 shade trees planted, including 35 fruit trees
  for food security (Climate Action, Life on Land).
- **Sholi Co-operative Mill (Rwanda)**: purchased via the Kundwa Women Coffee
  group, set up in 2008 by 30 women (Gender Equality, Reduced Inequalities).

## Sourcing & Transparency

- Product pages name producer/mill, variety, process and importer — e.g. the
  Ethiopia Banko Gotiti names the 650-smallholder Banko Gotiti wet mill and
  importer **Covoya**, and commits to buying from the same producers year on
  year "allowing our importers and producers to invest in the land and people
  behind the product".
- No FOB or farm-gate price figures are published, but an extensive
  "How to Read a Coffee" journal series (by Dale Harris & Alex Scott) covers
  variety, price and making informed choices.

## Philosophy & Quirks

- The name comes from C.P. Cavafy's poem **Ithaka** — "the journey, is
  repositioned not as a triumphant ending, but as the reason to begin". The
  business is framed as "an ongoing process of becoming", built around values
  rather than growth.
- Explicitly draws on E.F. Schumacher's *Small Is Beautiful*: economies
  designed around human scale; "efficiency without humanity" is rejected.
- Roasts light, and tells customers peak flavour arrives **around 21 days
  after roast** — "fresher can still be delicious, just a little more work!"
- FAQ promises "a real person reads it, not a bot" at hello@ithaka.coffee.

## Scraping Quirks

- **URL canonicalisation dedup**: products appear under multiple collection
  URLs, so `preprocess_product_url` collapses every
  `/collections/<slug>/products/<handle>` onto the canonical
  `/products/<handle>` form to avoid duplicate listings.
- **Third-party gear exclusion**: besides the base Shopify equipment filters,
  the Barista Hustle pitcher sold alongside the beans needs an explicit
  `barista-hustle` slug exclusion.

## Sources

- https://ithaka.coffee/
- https://ithaka.coffee/pages/aboutithaka
- https://ithaka.coffee/pages/why-ithaka
- https://ithaka.coffee/pages/cafe
- https://ithaka.coffee/blogs/news/un-sustainable-development-goals
- https://ithaka.coffee/products/ethiopia-banko-gotiti-washed
