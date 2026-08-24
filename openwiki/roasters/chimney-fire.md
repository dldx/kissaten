---
type: "Reference"
title: "Chimney Fire Coffee — Roaster Profile"
description: "Independent UK roastery in the Surrey Hills sitting on Denbies Wine Estate in Dorking — classic blends and single origins for homes and businesses, plus coffee subscriptions and compostable pods."
---

# Chimney Fire Coffee — Roaster Profile

## Overview

Chimney Fire Coffee Ltd is an independent UK coffee roaster in the Surrey
Hills, producing in Dorking, Surrey, and supplying ethically sourced beans to
homes and businesses across the United Kingdom. Its Shopify storefront at
chimneyfirecoffee.com lists 25 products in the Coffee collection, including
classic blends (REVIVAL CLASSIC BLEND, RANMORE SIGNATURE BLEND), single origins
and decaf, alongside coffee subscriptions, compostable pods and gift packs.

## Address

- Denbies Wine Estate, London Road, Dorking, Surrey RH5 6AA — United Kingdom

## Philosophy & Quirks

- Roasts in the Surrey Hills (Dorking), "great coffee, simply delivered"
  positioning with free UK shipping over £25.
- Classic-blend-led lineup (Revival Classic, Ranmore Signature) alongside a
  rotating single-origin range and a natural decaf.
- Also sells coffee subscriptions, Nespresso-compatible compostable pods and a
  "Chimney Fire Selection" gift pack; the roastery is open for visits and
  bean-to-cup experiences.

## Scraping Quirks

- UK market pinned (`country=GB` param plus `store_currency=GBP`) because GBP is
  the home market and curl_cffi requests can be geo/market-detected to a
  converted-currency market.
- The `coffee` collection also carries subscriptions, compostable pods and a
  gift pack — subscriptions and pods are excluded; non-bean variety/gift packs
  are retained and flagged (flag-don't-exclude) for the review queue.
- Canonical product URLs are `/products/<handle>` (collection segment stripped).

## Sources

- https://chimneyfirecoffee.com
- https://chimneyfirecoffee.com/pages/contact
- https://chimneyfirecoffee.com/collections/coffee