---
type: "Reference"
title: "Ozone Coffee — Roaster Profile"
description: "B Corp certified roaster born from Hasbean's 1999 Stafford market stall, now roasting every working day in Stafford and supplying cafés across London — home of the long-running 'In My Mug' subscription."
---

# Ozone Coffee — Roaster Profile

## Overview

Ozone Coffee (ozonecoffee.co.uk) is a B Corp certified speciality roaster whose
roasting happens at their Stafford roastery, with a chain of cafés in London
(Shoreditch, London Fields, St Paul's, Aldgate, Cheapside, Triton Square) and
work cafés as far afield as Leeds and Oxford. The modern company is a merger:
Stephen Leighton's Hasbean — started as a Stafford market stall in 1999 and one
of the UK's first online speciality roasters — joined forces with Ozone in 2018,
and the combined business rebranded fully as Ozone in 2024 (per their journal).
Shopify storefront; sells single origins, house blends (Hodson, Seasonal,
Paramount, Half Caff), tasting packs and the long-running **In My Mug**
subscription.

## Address

- Stafford roastery, Staffordshire, ST18 9QL — United Kingdom (street address
  not published; ST18 9QL is the collection postcode given on the shipping page)

## Sustainability

- **Certified B Corp** — "coffee as a force for good"; publishes an Impact
  Report alongside a Sourcing Report.
- Packaging switched from compostable to a recyclable bag made of **70%
  post-consumer recycled (PCR) LDPE** — with a candid explanation of why they
  moved on from compostables — plus recycling guidance for customers.

## Sourcing & Transparency

- "Long-term, transparent relationships" with producers, backed by a public
  directory of **30+ producer story pages** (Bolivia's Los Rodriguez family and
  Sol de la Mañana, Costa Rica's Don Mayo and Finca Licho, Ethiopia's Telila and
  Jimma producers, Thailand's Beanspire, Yemen's Haraz, and many more).
- Publishes a **Sourcing Report** alongside the Impact Report.

## Schedules & Shipping

- Coffee roasted **every working day** at the Stafford roastery; orders before
  07:30 GMT processed the same working day.
- **Free UK mainland delivery on orders over £30** and on all subscription
  orders; tiered service: £30–£149.99 Royal Mail Tracked 48 (2–4 days),
  £150–£199.99 Tracked 24 (1–2 days), £200+ DPD (also £8 flat / £12 Saturday
  option below £200).
- **In My Mug** subscription is roasted and dispatched every **Friday**, free
  via Royal Mail First Class.
- Local collection available from the Stafford roastery; international shipping
  via Royal Mail tracked services and UPS.

## Philosophy & Quirks

- Tagline: "the home of your **Ultimate Coffee Host**" — the team as "friendly
  coffee guides" for connoisseurs and newbies alike.
- Founder lore (from Stephen Leighton's own account): a 1999 Stafford market
  stall that sold three bags on day one, a garage roaster that literally caught
  fire, and a 2005 Cup of Excellence judging trip to Nicaragua.
- **"Test Roasts"** — an experimental/placeholder product line sold on the shop
  (excluded from the Kissaten catalogue; see below).
- Runs SCA training courses, a coffee quiz ("Find your flavour") and an Ozone
  Rewards loyalty club; sells rare preorders such as a single-producer Yemen lot
  from Ali Kabeer.

## Scraping Quirks

- The single `coffee` collection contains the **entire** bean catalogue
  (origin/varietal/process sub-collections are overlapping views), so the
  scraper fetches only that collection to avoid duplicates.
- Product URLs are canonicalised from `/collections/coffee/products/<handle>`
  to the site's `/products/<handle>` form.
- Exclusions change what lands in the catalogue: the `test-roasts` placeholder
  and any handle containing `-pack` (e.g. `bolivia-tasting-pack`) are filtered
  out, so Ozone's tasting packs never reach the catalogue.

## Sources

- https://ozonecoffee.co.uk/
- https://ozonecoffee.co.uk/pages/about-us
- https://ozonecoffee.co.uk/pages/sourcing
- https://ozonecoffee.co.uk/pages/b-corp
- https://ozonecoffee.co.uk/pages/sustainability
- https://ozonecoffee.co.uk/pages/shipping
- https://ozonecoffee.co.uk/blogs/journal/how-hasbean-began