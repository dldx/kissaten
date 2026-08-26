---
type: "Reference"
title: "The Picky Chemist — Roaster Profile"
description: "Beaufays, Belgium roastery offering analytical, method-specific light roast profiles and rare coffees."
---

# The Picky Chemist — Roaster Profile

## Overview

The Picky Chemist is a specialty coffee roaster in Beaufays, Belgium. The
roaster describes its approach as methodical and analytical, and offers coffees
through a Wix shop in three possible profiles: Omni-light, Espresso and
Ultra-light. Its catalogue includes high-end single-estate and competition-style
lots.

## Address

- Rue Auguste Nève 17, 4052 Beaufays, Belgium.

## Schedules & Shipping

- The order page says processing time is the maximum shown in the shop or basket
  and is adjusted with order volume and the roasting timetable. For nearby
  destinations it publishes: Belgium–Luxembourg €5, free from €40; France €5,
  free from €60; Luxembourg €3, free from €40. Other destination costs are
  calculated at checkout. Orders outside the EU cannot exceed €1,000 including
  shipping.

## Philosophy & Quirks

- The roaster does not offer dark roasts because it finds they obscure intrinsic
  bean qualities. It says it uses an analytical process for each new green
  coffee and may offer only one or two profiles when another does not produce a
  satisfactory cup.

## Scraping Quirks

- The Wix listing uses `data-hook="product-item-container"` links and marks
  unavailable products as “Out of Stock” on the card. The scraper removes the
  `2-60g` product, forces EUR, and sets every extracted bean to LIGHT with an
  Omni roast profile because those fields are not reliably represented in the
  page data.

## Sources

- https://en.thepickychemist.com
- https://en.thepickychemist.com/notre-offre-de-torréfaction
- https://en.thepickychemist.com/le-processus-de-commande
