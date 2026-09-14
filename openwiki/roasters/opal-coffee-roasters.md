---
type: "Reference"
title: "Opal Coffee Roasters — Roaster Profile"
description: "Small Derry/Londonderry roastery with a Squarespace shop of ten seasonal single origins, a Monday roast schedule, and per-product producer stories that name their importers."
---

# Opal Coffee Roasters — Roaster Profile

## Overview

Opal Coffee Roasters is a small specialty roastery in Northern Ireland running a
[Squarespace storefront](https://www.opalcoffeeroasters.co.uk) with a tight,
seasonal coffee menu — ten single origins at the time of writing: Migoti Hill
(Burundi), Kirunga Natural (Rwanda), San Ignacio (Peru), four Colombians (La
Esperanza, El Jaragual, Edinson Argote, Aponte Honey), two Kenyas (AA Thunguri,
Neyri AA) and Lillian Gallo (Brazil). All are offered in 200g and 1kg sizes,
priced in GBP. The business also runs a brew bar/retail store at the roastery,
sells brewing equipment, and does wholesale for cafes and coffee bars.

## Address

- Unit 9, Templemore Business Park, BT48 0LD — Northern Ireland, United
  Kingdom (per their site, which publishes the address without a city name;
  BT48 is the Derry/Londonderry postcode area).

## Sourcing & Transparency

- No standalone transparency page, but each product page carries a detailed
  "producer information" block — farm, producer, region, altitude and a farm
  story (e.g. Lillian Lisboa Gallo of Fazenda São José, Mantiqueira de Minas).
- Importers are credited on product pages where applicable — e.g. El Jaragual
  Colombia is "from our importers — Mi Cafe Trading Co.".
- They state they "choose our curated coffee menu intentionally, working with
  importers & producers who bring us the best quality from every origin".

## Schedules & Shipping

- **Roast cadence**: all orders are roasted each Monday; orders placed after
  1pm roll to the following week's roast schedule.
- **Dispatch**: shipping "no later by Tuesday"; they aim for delivery within
  48 hours of fulfilment.
- **Carriers & times**: Royal Mail Tracked 48 and UPS (1–2 working days), per
  their Shipping Terms page.
- No free-delivery threshold or per-country shipping rates are published
  anywhere on the site.

## Philosophy & Quirks

- Tagline on their second home page: **"Seasonal Coffee with character"**.
- Roast style: a "well developed, Light" roast aimed at "sweetness, clarity &
  brightness"; most coffees are omni roasts usable for espresso or filter.
  They recommend resting coffee 7+ days before brewing, with peak flavour at
  days 14–20.
- Modern brewing approach: longer espresso shots with a shorter extraction
  time (18g in, 42–45g out, 94°C), and filter recipes specifying water
  chemistry (200ml @ 120ppm, 95°C).
- Home-market pride: "to see coffee roasted here in Ireland sit on shelves
  across the uk allows us to connect with a wider community."
- The brew bar & retail store at the roastery keeps limited hours (Mondays
  09:00–14:00 per their site).

## Scraping Quirks

- The coffee listing lives at `/seasonal-coffee` and the shop has no `/shop`
  or `/coffee` URLs (both 404).
- Product slugs are opaque Squarespace hashes like
  `/seasonal-coffee/p/xqtpb8l7prv5ae9jh84w0tfq70yxqm` — no name-bearing slugs
  to match against.
- Sold-out coffees show a "Sold out" badge inside the `product-list-item`
  card and lose their "from £…" price; the scraper skips such cards.
- Brewing gear (Aeropress, Hario V60, Timemore scales, …) lives on a separate
  `/equipment` collection; the scraper additionally filters equipment/gift/
  subscription keywords so none of it lands in the coffee catalogue.
- A leftover Squarespace template page (`/services-sales-page-1`) contains
  generic "Explore Our Services" boilerplate with placeholder "LOGO" blocks —
  not real content.

## Sources

- https://www.opalcoffeeroasters.co.uk
- https://www.opalcoffeeroasters.co.uk/seasonal-coffee
- https://www.opalcoffeeroasters.co.uk/about-6-1 (Brew Bar & Roastery)
- https://www.opalcoffeeroasters.co.uk/group-events ("Seasonal Coffee with character" home page)
- https://www.opalcoffeeroasters.co.uk/faqs (Shipping Terms)
- https://www.opalcoffeeroasters.co.uk/terms-and-conditions
- https://www.opalcoffeeroasters.co.uk/seasonal-coffee/p/jfyiudg2dqn647g6z4yswp0oxcturl (Lillian Gallo Brazil)
- https://www.opalcoffeeroasters.co.uk/equipment
