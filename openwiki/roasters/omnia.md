---
type: "Reference"
title: "Omnia Coffee Roasters — Roaster Profile"
description: "Micro-roastery and coffee shop at 28 Industrial Street in Toronto, Canada, where founder and roast master Sameer Sidi roasts on site; coffees scored 85+ with the occasional 'Super Coffee' above 90 points."
---

# Omnia Coffee Roasters — Roaster Profile

## Overview

Omnia Coffee Roasters is a micro-roastery and coffee shop in Toronto, Ontario,
Canada, running a Shopify storefront at
[omniacoffeeroasters.com](https://www.omniacoffeeroasters.com). Founder and
Roast Master **Sameer Sidi**, who per their site has over 20 years of
experience in the coffee industry, sources, scores and roasts the coffees on
offer. The line-up is a small, rotating set of mostly Colombians and
Ethiopians (e.g. Ethiopia Halo Beriti Natural, Colombia Sidra Bourbon from
Finca Las Flores, Colombia Finca El Paraiso SL28, the Colombia Sugarcane
Decaf) plus the signature **Diablo** blend, and two subscription packs
(Roasters Subscription Pack, Diablo Subscription Pack).

## Address

- 28 Industrial Street, Toronto, Ontario — Canada (listed as "our retail
  store" on the contact page; postal code not published on site). Per their
  site, roasting happens on site at this location.

## Sourcing & Transparency

- No price-transparency figures (FOB, farm-gate) are published, but several
  product pages carry detailed producer write-ups: Finca Las Flores in
  Acevedo, Huila (producer Johan Vergara, part of a five-farm community with
  El Diviso and others), Don Jairo's Finca Castellano in Quindío, Colombia
  (farm elevation, year of establishment and full process protocol given),
  and traceability basics (region, altitude, varietal, process) on most
  beans.
- Wholesale is handled via email, with "exclusive bean orders" possible.

## Philosophy & Quirks

- Quality bar: per their site, they focus on coffees scoring **over 85
  points** on the cupping sheet, with the occasional **"Super Coffee"** —
  unique tasting notes and a score **above 90**.
- Seasonal rotation: coffee is treated as a seasonal crop; a departing
  coffee is replaced with "an equally satisfying" one, so favourite coffees
  are sold while the crop lasts.
- The shop doubles as a café and runs a **Barista Fundamentals and
  Foundations** course (CAD 400) from its `classes` collection.

## Scraping Quirks

- **Geo-currency pinning required**: Shopify Markets serves converted prices
  to datacenter IPs (GBP for UK IPs, USD for US ones), so the scraper appends
  `country=CA` to every paginated products.json request and forces the store
  currency to CAD so prices always come back in Canadian Dollars (the
  shipping policy confirms all prices are in CAD).
- **Identity disambiguation**: this omniacoffeeroasters.com business is in
  Toronto, Canada (CAD home market, Toronto contact details, BlogTO
  testimonials on the homepage). The UK "Omnia Coffee & Roaster" of the
  Nottingham press (89 Wollaton Rd, Beeston) is a different business with no
  online store — do not conflate the two.
- Subscription packs (`roasters-subscription-pack`, `2-pack-subscription`)
  are excluded via `exclude_slugs`, as are gift cards and equipment; the
  `classes` collection (the barista course) never enters the catalogue.
- Product URLs are canonicalised to `/products/<handle>`: the scraper strips
  the `/collections/frontpage` segment that products.json implies.
- No roast cadence, dispatch days, free-delivery threshold or per-region
  shipping rates are published anywhere on the site.

## Sources

- https://www.omniacoffeeroasters.com
- https://www.omniacoffeeroasters.com/pages/contact-us
- https://www.omniacoffeeroasters.com/pages/shipping-returns
- https://www.omniacoffeeroasters.com/pages/colombia-don-jairo-ice-fermentation
- https://www.omniacoffeeroasters.com/products/colombia-sidra-bourbon
- https://www.omniacoffeeroasters.com/collections/frontpage/products.json
