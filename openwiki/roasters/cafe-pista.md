---
type: "Reference"
title: "Café Pista — Roaster Profile"
description: "Montréal roaster that began as the world's first human-powered bike café, now roasting on a low-emission Loring with per-lot price transparency (price paid vs C-market) on every single-origin page."
---

# Café Pista — Roaster Profile

## Overview

Café Pista is a Montréal, Québec specialty roaster founded in 2014 by Maxime, then
20, as "Le Pista Café Mobile" — a bike café powered entirely by human energy, with
coffee ground by pedalling and billed as the world's first human-powered café.
Today it runs three Montréal cafés (Beaubien, Masson, Quartier des Spectacles on
Boulevard St-Laurent) and roasts its own coffee, sold through a French-first
bilingual Shopify storefront alongside matcha, brew equipment and cold brew.

## Address

- 2650 rue Masson, Montréal, QC H1Y 1W2, Canada — listed as the return address in
  the refund policy (per their site); the page does not label a dedicated roastery
  address.

## Sustainability

- Roasts on a low-emission ("carbonite") Loring roaster and delivers in electric
  vehicles, per their history page.
- Reports cutting in-store waste by ~70%, composts all organics, and recycles both
  its own and competitors' coffee bags; encourages bulk purchases and reusable cups.

## Sourcing & Transparency

- Works directly with farms plus a small set of selected importers, aiming for
  long-term relationships: "the same origins return to our shelves year after
  year" (per their history page). Lots are cupped blind by the roasting team.
- Claims to pay producers more than three times the commodity (C-market) price.
- Product pages carry a "Transparence" accordion with per-lot figures, e.g. for
  the Bookkisa lot: price paid 6.55 CAD/lb vs C-market at 4.34 CAD/lb, a 7-year
  partnership via importer Osito Coffee, lot size 20 x 60 kg, and a cup quality
  score of 88.

## Roasting & Equipment

- Loring low-emission roaster (per their site); most coffees roasted "brown but
  light" (light roast) to highlight origin character, per their refund-policy FAQ.

## Schedules & Shipping

- Free delivery in Québec on orders of CAD 49+ (site-wide banner). No per-region
  shipping rates are published on the shipping-policy page (it is empty), and no
  roast/dispatch schedule is published.

## Philosophy & Quirks

- The company's origin story is its signature: a pedalling-powered coffee trike
  from 2014, which still anchors the brand ("Pista" = track).
- Retail coffee bags are sold in several grind options (En grain, Espresso,
  Italienne, Aeropress, Filtre, Presse française) at the same price per size.

## Scraping Quirks

- The catalog mixes three price channels: retail products, `wholesale-only`-tagged
  duplicates of the same coffees at bulk prices (handles like `saison_ws`,
  `la-linda-ws`), and `wholesale-only` private-label bags for partner businesses
  (Café Collectif). The scraper filters on the French product type
  `Sac de café` and drops the `wholesale-only` / `subscription` tags.
- Even the retail catalog keeps parallel old/new listings of the same coffee under
  different handles (e.g. `bookkisa` and `bookkisa-lave-ethiopie-1`), so some
  beans appear twice with different slugs.
- Shopify Markets geo-converts prices to GBP for datacenter IPs (Bookkisa 28.00
  CAD renders as 16.00 GBP); the scraper pins `country=CA` on the products.json
  listing and product pages and forces the store currency to CAD.
- The site is French-first; catalog data (`titles`, `body_html`, product types)
  is French, so extraction forces English translation. Curated trios
  ("Trio de cafés", "Ensemble dégustation") flow through the tasting-kit review
  queue via French kit patterns, never excluded.
- Price-transparency data (Transparence accordion) and the origin detail block
  exist only on rendered product pages, not in products.json `body_html`, so the
  scraper prunes pages to `div.product-information` rather than running JSON-only.

## Sources

- https://cafepista.com/pages/notre-histoire
- https://cafepista.com/pages/espaces
- https://cafepista.com/policies/refund-policy
- https://cafepista.com/policies/shipping-policy
- https://cafepista.com/products/bookkisa
- https://cafepista.com/collections/all/products.json
