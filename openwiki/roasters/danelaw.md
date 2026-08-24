---
type: "Reference"
title: "Danelaw Coffee — Roaster Profile"
description: "Yorkshire (Holmfirth) speciality roaster on Shopify at danelawcoffee.co.uk with over 50 Great Taste Award stars since 2017, scored coffees ('SCORE: 84+') and its own Holmfirth coffee shop Bjorn."
---

# Danelaw Coffee — Roaster Profile

## Overview

Danelaw Coffee is a Yorkshire speciality coffee roaster on a Shopify storefront
at danelawcoffee.co.uk (danelaw.coffee and the www host both 301 there). Its
coffees have won over 50 Great Taste Award stars since 2017 and some carry a
cupping-score label ("SCORE: 84+", e.g. Brasil Natural). Since October 2025 it
has also run the Holmfirth coffee shop Bjorn — a Danelaw brand (rebranded from
Yellow B Roasters), not a second roaster; see [Bjorn](bjorn.md).

## Address

- Meltham Mills Industrial Estate, Unit D11 Gate 4, Meltham, Holmfirth HD9 4DS — United Kingdom.

## Schedules & Shipping

- Orders under £50: £5.25; orders of £50 or more: free UK delivery (the
  homepage banner advertises free shipping on mainland UK orders over £30).
- In-stock orders dispatched within 1–2 working days; Royal Mail 1–3 working
  days, DPD usually next working day (per their shipping policy).

## Philosophy & Quirks

- "Approachable Speciality Coffee" — the founder is a 2-time UK Coffee in Good
  Spirits Champion, Q-Arabica grader and World Barista Championship judge.
- The name recalls the 9th-century Viking Danelaw that covered his home
  counties; blends carry Norse names (Mjólka, Fjødr, Langhūs, Dægr, Nott…).
- Owns the Holmfirth coffee shop Bjorn ("Holmfirth's home for espresso"),
  serving its signature house blend Necessities and guest Red Panda.

## Scraping Quirks

- Single curated umbrella collection `all-coffee` is the crawl source;
  `collections.json` over-counts (45 claimed) vs 28 published products.
- `filter` / `espresso` / `decaf` / `great-taste` / `bjorn-speciality-coffee`
  are all strict subsets (verified 0 missing) — no merge needed.
- Bjorn-branded products (red-panda, blend-necessities, brown-ben, gasharu…)
  are Danelaw's own freshly roasted coffee — kept, not a separate roaster.
- Norse Code liqueur (`norse-code` collection) and equipment
  (`sage-coffee-machines`) excluded as non-coffee.
- `espresso-explorer-pack-2026-4x250g` and
  `nott-coffee-by-danelaw-decaf-discovery-4x250g` samplers flagged
  `is_tasting_kit` into the admin review queue.
- Canonical product URLs are `/products/<handle>`.

## Sources

- https://danelawcoffee.co.uk
- https://danelawcoffee.co.uk/pages/my-story
- https://danelawcoffee.co.uk/policies/shipping-policy
