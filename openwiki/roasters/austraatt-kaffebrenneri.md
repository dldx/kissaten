---
type: "Reference"
title: "Austrått Kaffebrenneri — Roaster Profile"
description: "Small Norwegian roastery in Voll supplying HORECA and an online range that changes with season and availability."
---

# Austrått Kaffebrenneri — Roaster Profile

## Overview

Austrått Kaffebrenneri AS is a relatively small roastery in Voll, Norway, with its main business focused on hotels, restaurants and catering. The online shop offers single-origin coffees and blends whose selection changes with season and availability, alongside HORECA and professional-equipment categories. Its storefront is a MyStore shop.

## Address

- Vollvegen 38, 4354 Voll, Norway.

## Schedules & Shipping

- The roastery's “Om oss” page says coffee is normally sent weekly. The shop also advertises worldwide shipping, but the consulted pages do not publish destination-specific rates or a free-delivery minimum.

## Philosophy & Quirks

- Austrått says it makes every effort to roast coffee in a way that preserves the coffee's character, process and origin. Its catalogue includes coffees from most coffee-producing countries and changes with the seasons.

## Scraping Quirks

- The scraper reads the Norwegian stock marker `På lager` and skips cards without it, so a sold-out card is not treated as an extractable product. It trims product pages to `main > section` before AI extraction, forces currency to NOK, and excludes subscriptions, brew bags, drip bags, capsules and the `espresso-og-baristamaskin` URL pattern.

## Sources

- https://www.austraattkaffebrenneri.no/pages/om-oss
- https://www.austraattkaffebrenneri.no
- https://www.austraattkaffebrenneri.no/categories/kaffe
