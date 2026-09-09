---
type: "Reference"
title: "Ethica Coffee Roasters — Roaster Profile"
description: "Toronto specialty roaster named after Spinoza's Ethica, roasting at a Sterling Rd roastery-café with single-origin espressos, filters and a rotating SPECTRUM series."
---

# Ethica Coffee Roasters — Roaster Profile

## Overview

Ethica Coffee Roasters is a specialty coffee roaster based in Toronto, Ontario, roasting and serving from a high-ceilinged industrial roastery-café on Sterling Rd ("Roasted in Toronto", per their site). The name is inspired by Spinoza's *Ethica Ordine Geometrico Demonstrata*, and the company frames its values as Ethics, Quality and Expertise. The catalogue centres on single-origin espressos and filters (Brazil, Ethiopia, Colombia, Guatemala, Mexico, Burundi, China) plus house blends (Ethica Espresso, Ethica Filter, a sugarcane-processed decaf) and a rotating "SPECTRUM" single-origin series. The storefront is a headless Shopify build (Next.js front-end, Shopify backend).

## Address

- Unit 104 – 213 Sterling Rd, Toronto, ON, Canada (roastery-café; open Mon–Fri 8AM–5PM, Sat–Sun 8AM–6PM per their site)

## Sustainability

- Coffee bags are supplied by Dutch Coffee Pack (Netherlands): CO₂-compensated, 100% plastic with a high oxygen barrier, collected with plastic waste per their FAQ.

## Sourcing & Transparency

- No FOB / farm-gate price figures are published. Product pages name their green importers — e.g. Ethica Espresso is described as a peak of the partnership with importer Orange Brown and tells the multi-generation Barbosa family story from Carmo do Paranaíba, Minas Gerais, Brazil.

## Schedules & Shipping

- Orders are processed within 2 business days; items typically arrive 5–7 business days from shipment (Canada Post), per their shipping policy.
- Free Canadian shipping over $60 CAD; flat $10 CAD for the rest of Canada; free café pickup in Toronto.
- Free shipping to the USA over $90 USD (duties and taxes covered by Ethica); other US orders calculated at checkout; worldwide shipping elsewhere by email arrangement.
- Returns permitted within 15 days of receipt, subject to authorisation.

## Philosophy & Quirks

- The Spinoza-inspired name frames an ethics-first mission: "connect people through exceptional coffee while honouring farmer's stories" (per their About page).
- Product pages include a fixed "Ethica's Brew Recipe" spec (method, dose, yield, time, temperature, ratio) for each coffee.
- The roastery-café interior has been featured on bestcafedesigns.com, listed as a "Top 100 Architecture Blog Worldwide" (per their site).

## Scraping Quirks

- Headless Shopify: the classic `/products.json` endpoints return the site's 404 page, so discovery is from the server-rendered `/shop` listing and detail extraction uses Playwright — the React Server Components payload only becomes readable DOM after client hydration.
- The `/shop` listing mixes beans with equipment, merch and subscriptions; sold-out beans stay listed with a "Sold Out" badge inside their card.

## Sources

- https://www.ethicaroasters.com/
- https://www.ethicaroasters.com/about
- https://www.ethicaroasters.com/shop
- https://www.ethicaroasters.com/faq
- https://www.ethicaroasters.com/shipping-policy
- https://www.ethicaroasters.com/product/ethica-espresso
