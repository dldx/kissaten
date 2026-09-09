---
type: "Reference"
title: "Spring Valley Coffee — Roaster Profile"
description: "Nairobi roaster established 2009, roasting Kenyan coffee at origin and named Best New Coffee Shop at the 2026 London Coffee Festival Awards for its Islington café."
---

# Spring Valley Coffee — Roaster Profile

## Overview

Spring Valley Coffee is a specialty roaster in the Spring Valley neighbourhood of Nairobi, Kenya — the area where one of Kenya's first coffee estates was established in 1905 — and has been roasting there since 2009 ("roasted at origin", keeping more of the coffee's value in Kenya). Its online shop sells Kenyan single origins such as Halisi, Nuru, Elgon (Endebess Estate on Mt. Elgon), Karimikui, Mukuyuni and a rotating "Roasters' Select" series, plus capsules. The company runs a dozen cafés across Nairobi and opened its first international café at 24 Camden Passage, Islington, London in June 2025, which per their site was named Best New Coffee Shop at the 2026 London Coffee Festival Awards.

## Address

- The Roastery, Springette, Lower Kabete Road, Spring Valley, Nairobi, Kenya

## Sustainability

Per their sustainability page, the company describes itself as "a purpose-led business for people & planet", dedicated to "economic sovereignty at origin" — keeping a greater share of value with Kenyan producers — and publishes a downloadable Sustainability Action Plan (June 2026). The page also commits to a zero-political-spending policy, compliance with the Kenyan Bribery Act, and annual review of trade-association memberships.

## Sourcing & Transparency

Sourcing is entirely Kenyan, from named estates and washing stations — e.g. the 758-hectare Endebess Estate on the western slopes of Mt. Elgon (Elgon) and Maguta Estate in the Muruguru hills of Nyeri (Roasters' Select #6 "Nili"). Per their sustainability page, they commit to "transparency of sourcing (where available)" and tailored support and training for supply-chain workers, though no FOB/farm-gate price figures are published on the site.

## Philosophy & Quirks

- Tagline: "Incredible Kenyan coffee, roasted at origin"; mission: "to catalyse change one coffee at a time".
- Named after the Spring Valley neighbourhood of Nairobi; roasting there since 2009.
- Product names are Swahili/Kenyan references — e.g. "Nili" means "indigo" in Swahili, after the deep-purple cherries of the carbonic-maceration nano lot it names.
- The Roasters' Select numbered series commemorates company milestones (#6 marked the London opening and the 2026 London Coffee Festival award).

## Scraping Quirks

- The roaster is Kenyan but the default storefront (`www.springvalleycoffee.com`) trades in **GBP** (Shopify base currency, rate 1.0), with a Kenya/UK market switcher on the homepage; the KE market serves different prices (e.g. a £16.00 bag shows 22.95 under the KE market). The scraper pins `store_currency = "GBP"` so market detection cannot override it.
- Curated feed is `/collections/coffee/products.json` (roasted coffee bags only); capsules and the London cupping "Experience" live outside it. Canonical product URLs are `/products/<handle>`, so the collection segment is stripped.

## Sources

- https://www.springvalleycoffee.com/
- https://www.springvalleycoffee.com/pages/sustainability
- https://www.springvalleycoffee.com/pages/cafes
- https://www.springvalleycoffee.com/products/nili
- https://www.springvalleycoffee.com/products/elgon-1
