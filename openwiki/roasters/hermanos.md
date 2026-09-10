---
type: "Reference"
title: "Hermanos Coffee Roasters — Roaster Profile"
description: "London roaster (est. 2018 in Walthamstow) bringing single-origin Colombian direct-trade coffee to the UK — brothers Victor & Santiago Gamboa, 'paying beyond Fairtrade prices', now in Selfridges."
---

# Hermanos Coffee Roasters — Roaster Profile

## Overview

Hermanos ("brothers" in Spanish) is a London roastery specialising entirely
in single-origin Colombian coffee, founded by brothers Victor and Santiago
Gamboa together with Adnan, who spent time in Colombia learning about coffee.
Their first pop-up was in Walthamstow in 2018, and they now run a string of
London cafés (Portobello Road, Victoria Station, Blackhorse Lane, King's
Cross, Columbia Road and more). The Shopify storefront at
[hermanoscoffeeroasters.com](https://hermanoscoffeeroasters.com) sells
classic Colombian profiles plus seasonal and exotic micro-lots; the brand
calls itself London Coffee Festival award winners and is stocked in
Selfridges (per their site).

## Address

- Roastery: London, United Kingdom — full address not published on site
  (retail café locations across London are listed separately on the site).

## Sustainability

- Uses sustainable, eco-friendly packaging and seals roasts immediately
  after roasting and cooling.
- Publishes a sustainability programme built around greater traceability of
  coffee and origin, respecting the complexity of coffee production, and
  showcasing the work of individual farmers.

## Sourcing & Transparency

- **Direct trade** with Colombian farmers: daily check-ins on fair
  treatment, frequent UK-team visits to partner farms in Colombia, and — per
  their roastery page — "paying beyond Fairtrade prices" to give farmers
  financial stability and the ability to reinvest in their farms.
- A counter on the farmers page tracks over **30,000 kg of green beans
  roasted** to date.
- Sourcing spans classic Colombian profiles and smallholder micro-lots;
  regions referenced include Tolima and Quindío.

## Schedules & Shipping

- Free UK delivery on coffee orders over £25 (US customers: free over
  $125); qualifying orders ship next-day.
- Non-qualifying UK orders: £3.50 next-day delivery (DHL and Royal Mail).
- International shipping via FedEx with cost estimates at checkout; import
  duties/taxes are the buyer's responsibility.

## Philosophy & Quirks

- The mission is explicitly cultural: "bringing the warmth, vibrance, and
  knowledge of Colombia to the world", with bilingual English/Spanish
  headings (Tostión Auténtica, Nuestros Caficultores) throughout the site.
- Freshness is the headline promise: small-batch roasting, immediate
  sealing in eco-friendly packaging, and "make it to checkout today… at your
  door tomorrow".
- The company has opened a **franchising programme**
  ([hermanosfranchise.co.uk](https://hermanosfranchise.co.uk/)) alongside its
  cafés and wholesale arm.
- Sells a branded **Tasting Kit** (50g/100g sampler product).

## Scraping Quirks

- Non-coffee products are filtered by handle substring: `-pods`,
  `-capsules` and `-gift-set` URLs are excluded.
- The site's **Tasting Kit** (`tasting-kit-50g-100g`) is *not* excluded — it
  matches the base scraper's `tasting-kit` URL pattern and is flagged
  `is_tasting_kit` / `requires_review`, landing in the admin review queue
  rather than public search.

## Sources

- https://hermanoscoffeeroasters.com/
- https://hermanoscoffeeroasters.com/pages/our-story
- https://hermanoscoffeeroasters.com/pages/our-farmers
- https://hermanoscoffeeroasters.com/pages/our-roastery
- https://hermanoscoffeeroasters.com/pages/faqs
- https://hermanoscoffeeroasters.com/pages/sustainability
- https://hermanoscoffeeroasters.com/policies/shipping-policy
