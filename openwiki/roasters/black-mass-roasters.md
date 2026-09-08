---
type: "Reference"
title: "Black Mass Roasters — Roaster Profile"
description: "Brisbane (Meanjin) Australia specialty roaster on a Shopify storefront priced in AUD — heavy-metal/occult branding with gothic product names, roasted in Brisbane."
---

# Black Mass Roasters — Roaster Profile

## Overview

Black Mass Roasters is a specialty coffee roaster based in Brisbane (Meanjin),
Queensland, Australia, roasting on a Shopify storefront priced in AUD. The
brand leans into heavy-metal and occult imagery — tagline "Sacrificial
Offerings", product names like VITRIOLIC HISS, TONGUE OF THE SERPENT and THE
INFERNAL TRINITY — while the coffee line-up is serious specialty: rotating
single origins (Honduras, Colombia, Bolivia, Ethiopia, Kenya, Nicaragua), house
blends, an experimental decaf and multi-bag bundles. The site states "Roasted
in Brisbane (Meanjin), Australia" and ships worldwide.

## Address

- Brisbane (Meanjin), Queensland, Australia — full roastery street address not
  published on site.

## Schedules & Shipping

- Orders are "roasted ... to order" in spirit: the shipping policy says to
  "allow a brief period for roasting and dispatch" and aims to dispatch within
  1–3 business days of receiving an order.
- Australia: Standard shipping 3–5 business days at a fixed $9.95 rate; Express
  1–4 business days at a fixed $12.95 rate.
- International: Standard 6–30 business days and Express 5–20 business days,
  both at varied rates. No free-delivery minimum is published.
- US orders are charged an AUD $1.69 customs processing fee, plus 10% for
  applicable US duties and taxes on all products *excluding* coffee (per their
  shipping policy).

## Philosophy & Quirks

- Heavy-metal / occult-themed branding throughout: "Sacrificial Offerings",
  "Shipping Worldwide", and a header quote from Emily Dickinson — "Be Mine the
  Doom — Sufficient Fame — To perish in Her Hand!"
- Coffee releases are named like metal songs (VITRIOLIC HISS, EXHUMATION
  RITES, ABHORRENT PASSAGE, METAPHYSICAL MELADIES) with blends styled as
  liturgical objects (CHALICE, CATHEDRAL, EFFIGY, VAJRA, THE INFERNAL TRINITY).
- The site acknowledges the Jagera & Turrbal peoples as the traditional
  custodians of the land on which the roaster operates.
- General enquiries via an on-site form or hello@blackmassroasters.com.

## Scraping Quirks

- No dedicated "coffee" collection exists: the canonical live coffee set is the
  `view-all-live-offerings` collection, which the scraper filters on Shopify
  `product_type == "Coffee"` to keep single origins, blends, decaf and
  multi-bag bundles.
- The genuine recurring "Blend Subscription" handles are excluded via
  `exclude_slugs` ("subscription"), while multi-bag bundles (Roasters Choice
  Bundle 'Triune', THE INFERNAL TRINITY) are kept — any that the AI extractor
  recognises as tasting kits flow through `_apply_product_flags` into the admin
  review queue rather than being silently dropped.
- Product URLs are canonicalised to the no-collection `/products/<handle>` form
  the live site serves.
- The store runs Shopify Markets with currency geolocation, so the scraper pins
  `store_currency` to AUD and removes the `Accept-Language` header so a
  datacenter IP is never stamped with converted prices.

## Sources

- https://blackmassroasters.com
- https://blackmassroasters.com/pages/about
- https://blackmassroasters.com/pages/contact
- https://blackmassroasters.com/policies/shipping-policy
- https://blackmassroasters.com/collections/view-all-live-offerings/products.json