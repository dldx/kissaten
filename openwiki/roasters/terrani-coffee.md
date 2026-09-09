---
type: "Reference"
title: "Terrani Coffee — Roaster Profile"
description: "Nairobi-based Kenyan specialty roaster sourcing Arabica directly from local farmers; signature Kawa Noir dark roast, washed and anaerobic natural singles, plus drip-bag boxes and sampler pouches"
---

# Terrani Coffee — Roaster Profile

## Overview

Terrani Coffee is a Nairobi-based Kenyan specialty coffee roaster focused on bringing out the best of Kenyan coffee (per their site). They source high-quality Arabica beans directly from local farmers and roast in small batches, selling roasted-to-order beans across Kenya through a Shopify storefront at www.terranicoffee.store. The lineup is compact — a signature dark-roast espresso blend ("Kawa Noir"), a Fully Washed medium roast, and an Anaerobic Natural medium roast, all 100% Kenyan Arabica — supplemented by 120g sampler pouches, an 80g sampler tin, and single-serve drip coffee boxes. Their tagline is "Sharing Stories One Cup at a Time" (per their site logo).

## Address

- Nairobi, Kenya — full address not published on site; the contact page offers a form only.

## Schedules & Shipping

- Free delivery on orders above KES 3,000 within Nairobi (site announcement banner).
- Delivery is offered "across Kenya"; shipping costs are calculated at checkout and no per-region rates are published.
- Beans are described as "freshly roasted and delivered across Kenya" (per their site); no explicit roasting cadence or dispatch days are published.

## Philosophy & Quirks

- Everything is 100% Kenyan Arabica sourced directly from local farmers; the range is organised by process (fully washed vs anaerobic natural) and roast (medium vs the dark "Kawa Noir" blend) rather than by farm or lot (per their site).
- The drip coffee boxes contain five single-serve drip bags, each printed with a "witty message" (per their product copy).
- Grind size is offered as a variant option (whole beans, fine for espresso/Moka pot, medium for pour-over/French press/home machines) rather than separate products.

## Scraping Quirks

- Sampler pouches (120g), the 80g sampler tin, and drip coffee boxes flow through the tasting-kit review queue (`is_tasting_kit` / `requires_review` flags) — they must not be excluded by slug.
- Product URLs are canonicalised to the no-collection form `/products/<handle>` (the site's own nav links omit the collection segment).
- Prices are in KES with `Shopify.currency` rate 1.0; the scraper pins `store_currency = "KES"` defensively against geolocation-based conversion.

## Sources

- https://www.terranicoffee.store/
- https://www.terranicoffee.store/pages/about-terrani
- https://www.terranicoffee.store/products/anaerobic-natural-medium-roast-250g
- https://www.terranicoffee.store/collections/freshest-batch-of-coffee/products.json
