---
type: "Reference"
title: "Freda Coffee — Roaster Profile"
description: "Sussex-based independent speciality micro-roaster on Shopify at freda.coffee with 7 single-origin coffees in 250g, GBP, roasted weekly on a Loring Eco Smart."
---

# Freda Coffee — Roaster Profile

## Overview

Freda is a Sussex-based independent speciality micro-roaster on a Shopify storefront at freda.coffee. It carries 7 single-origin coffees — Cajamarca Peru, Kihuyo AA Kenya, La Bolsa Guatemala, Black Rain Rwanda Inzovu, Black Dog rotating, Decaf Colombia, Otavio Reis Brazil — roughly £12.50–£15.30/250g, GBP. Subscriptions and brewing equipment are excluded.

## Address

- Sussex, England — United Kingdom (Worthing per one listing, Brighton/Hove per another; sister company Bond Street Coffee in Brighton packs the beans)

## Philosophy & Quirks

- Roasted weekly on a Loring Eco Smart; named after the founder's grandmother Freda.
- Beans are packed by sister company Bond Street Coffee, Brighton (café since 2014).
- Offers "Chosen By Freda" subscriptions.

## Scraping Quirks

- The listed domain fredacoffee.com never existed (DNS dead, zero Wayback) — the real store is freda.coffee (Shopify).
- The curated collection handle is `all-coffee-copy` ("Coffee Beans"); products.json counts (7) differ from collections.json advertised counts (48–50, stale).
- Dawn theme — bean specs (SCA score, altitude, variety, transparency) live in the page's Info/Story/Transparency accordions (some, e.g. Kihuyo, have empty body_html), so the scraper page-scrapes with accordion pruning.
- Canonical product URLs are `/products/<handle>`; currency pinned to GBP.

## Sources

- https://freda.coffee
- https://freda.coffee/collections/all-coffee-copy