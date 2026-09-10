---
type: "Reference"
title: "Darkwoods Coffee — Roaster Profile"
description: "B Corp roastery in a converted Victorian mill in Marsden, Huddersfield — recertified 2024 with a 147.4 score, 100+ Great Taste Awards including three Golden Forks, and a 'Beyond Specialty' philosophy with at least 2% of turnover given to charity."
---

# Dark Woods Coffee — Roaster Profile

## Overview

Dark Woods Coffee was set up in 2014 by three friends with deep coffee
resumes: Damian (ex senior roaster/buyer, Cup of Excellence and Best of Panama
judge), Paul (founder of Coffee Community, co-writer of the City & Guilds
Barista Qualification, Head Judge for World Latte Art) and Ian (community
outreach veteran and Farmers' Voice Radio director). They roast in a converted
Victorian textile mill at the foot of the West Yorkshire Pennines, which also
houses their barista school, open by appointment Monday–Friday. The Shopify
storefront sells a year-round Core Range named after the local
landscape (Under Milk Wood, Crow Tree, Deer Hill, Black Hill, Lamplight Decaf)
plus a rotating seasonal Producer Series.

## Address

- Holme Mills, West Slaithwaite Road, Marsden, Huddersfield HD7 6LS,
  West Yorkshire — United Kingdom

## Sustainability

- **Certified B Corp since 2020**; recertified in 2024 with a score of 147.4,
  which they call one of the leading B Corp scores globally. Publishes annual
  B Corp Impact and transparency reports.
- **Donates at least 2% of annual turnover** to charities and community
  groups — including almost £30,000 in small grants to Huddersfield-area
  organisations over two years (warm spaces, hot meals, forest schools,
  mountain rescue) — and since 2022 funds a children's home in Bensa,
  southern Ethiopia (~30 children) with Ardent Coffee.
- Food-service (and soon retail) packaging is **home-compostable** with an
  industrially compostable valve; more than thirty wholesale customers have
  switched to reusable/returnable containers.
- Runs the **Dark Woods Foundation**, a UK registered charity aligned with the
  UN SDGs, and has long supported World Coffee Research.

## Sourcing & Transparency

- Green coffee makes up over 70% of total purchasing; bought mostly through
  long-standing relationships with around eighteen producer cooperatives and
  family-run farms, with **99% of buying agreed via forward contracts** for
  producer security.

## Schedules & Shipping

- Orders are usually **dispatched within 3 working days**; orders placed after
  9.30am are processed the following day. Allow up to 5 working days for
  delivery.
- **Free tracked delivery on UK orders over £35** (UK mainland only; Royal
  Mail Tracked 24/48 and DPD). Other charges vary and are shown at checkout —
  and they ship **UK only**.
- Subscriptions carry a 5% discount with the same free-shipping threshold.

## Philosophy & Quirks

- **"Beyond Specialty"**: the belief that SCA 80+ point buying is the bare
  minimum for an ethical roaster, not a differentiator.
- Award machine: well over 100 Great Taste Awards, including **three Golden
  Forks** (2024–2026 winners listed on their site).
- Core Range blends are named after the Yorkshire landscape around the
  mill — moorland, drystone walls and ancient woodland.
- Off-beat merch line includes "notNeutral" mugs; a barrel-aged coffee
  (Common Grounds) sits in the core lineup.

## Scraping Quirks

- **Heavy non-coffee catalogue**: the scraper excludes a long slug list
  (gift tins, chocolate, merchandise/apparel, mugs, capsules/pods, cold-brew
  cans, easy-pour, subscriptions) — check the `exclude_slugs` list if new
  non-bean product lines start landing in the catalogue.
- **Bean data hidden in accordions**: origin, process, variety, altitude, roast
  and producer story live inside collapsible `div.product__accordion`
  sections; `preprocess_product_soup()` strips the page down to those
  accordions before AI extraction (preserving a body so the Shopify JSON
  context injection still works).

## Sources

- https://darkwoodscoffee.co.uk/
- https://darkwoodscoffee.co.uk/pages/about
- https://darkwoodscoffee.co.uk/pages/values
- https://darkwoodscoffee.co.uk/policies/shipping-policy
- https://darkwoodscoffee.co.uk/pages/contact
