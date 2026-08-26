---
type: "Reference"
title: "Loumi Coffee — Roaster Profile"
description: "Ukrainian specialty roaster with small-farm sourcing claims, a stated producer-pay commitment and a fixed animal-support contribution per bag."
---

# Loumi Coffee — Roaster Profile

## Overview

Loumi Coffee is a Ukrainian specialty coffee roaster and online shop. Its catalogue separates espresso and filter coffees and also sells drip coffee, tea, minerals and accessories. The site presents the business through the idea that the true essence is found within, and names Kostyantyn Strelnykov as co-founder and roaster.

## Address

- Ukraine — full roastery address and city are not published on the accessible site.

## Sustainability

- Loumi says it uses sustainable production practices to reduce environmental impact and protect nature.
- It also states that **UAH 20 from every coffee bag** is directed to foundations caring for animals, with different initiatives selected so the support remains consistent and tangible.

## Sourcing & Transparency

- Loumi says it works with small farms, provides fair remuneration for farmers and supports local communities. No per-lot FOB, farm-gate or price-paid-to-producer figures are published on the pages checked.

## Schedules & Shipping

- Orders paid by **14:00** are sent the same day; later orders are processed the next day. The stated working schedule is Monday–Friday.
- Within Ukraine, delivery is by Nova Poshta branch or courier, with Kyiv pickup available at a partner café. International delivery is arranged by a manager after the customer comments on the order; shipping cost is stated to follow Nova Poshta tariffs. No free-shipping threshold is published.

## Philosophy & Quirks

- The site combines “more than coffee,” fair trade, conscious production and quality as its four short brand pillars. It also identifies the shop as pet-friendly in its charitable positioning.

## Scraping Quirks

- The scraper assumes four catalogue pages (`/catalog/coffee-beans/{1..4}/`), extracts links from `a.elementor-element`, removes URLs containing `pack-`, and deletes a “more coffee” block containing the Ukrainian text `більше кави` before AI extraction. It rejects an extracted bean if a declared price has a non-UAH currency.

## Sources

- https://loumi.coffee
- https://loumi.coffee/terms-privacy/
- https://loumi.coffee/about-us/
