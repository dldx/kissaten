---
type: "Reference"
title: "Roast Republik — Roaster Profile"
description: "Nakuru-based Kenyan roastery (Roast and Grind Africa Ltd) roasting single-origin Kenya AA/AB/C beans and the PLUG house blend, pairing its shop with a roasting academy, a green-coffee sourcing service and a mobile coffee bar."
---

# Roast Republik — Roaster Profile

## Overview

Roast Republik is the coffee brand of Roast and Grind Africa Ltd, a Nakuru-based Kenyan roastery trading online as Kenyan-Coffee.com (storefront built on Zoho Commerce; the roastery also appears under the name "Nakuru Coffee Roastery"). The company positions itself around the tagline "Coffee. Education. Experiences.", combining a retail coffee shop, a Coffee Roasting Academy with certificate courses, wholesale supply, a mobile coffee-bar service and a green-coffee sourcing service. Its retail range is all Kenyan: single origins sold by grade — HUSTLE (AB), SOFT LIFE (AA), MBOGI (C) — plus the PLUG house blend and the MOTO home-use beans, in 100 g–1 kg packs (KES 220–800 retail). Per their site, the stated vision is that Kenyan coffee "should not only be exported around the world. It should also be enjoyed, understood and valued at home."

## Address

- Cigma Building, 4th Floor, Door 4A, Nakuru, Kenya (per their contact page — listed as "Visit Our Roastery"; the site's structured data additionally gives "Nakuru/Nairobi Main Highway, Mburu Gichua Road, Nakuru, Rift Valley, 20100, Kenya")

## Sourcing & Transparency

No producer-level price transparency is published. The roastery runs a paid **green-coffee sourcing service** for roasters, cafés, traders and exporters: a sourcing fee of **KES 130 per kg** covering supplier identification, negotiation, quality verification and batch testing, with cupping, documentation and delivery arranged at additional cost (per their Green Coffee Sourcing page).

## Schedules & Shipping

- Dispatch target: standard orders are prepared for dispatch within **1–2 business days** after payment confirmation (per their Shipping & Delivery policy, effective 14 August 2026).
- Delivery across Kenya via courier partners; major-town deliveries commonly arrive within **1–3 business days after dispatch**.
- Delivery charges depend on destination, order size and courier rates and are shown at checkout — no free-delivery minimum is published.

## Philosophy & Quirks

- The retail bean names double as Kenyan grade descriptors: HUSTLE Kenya **AB**, SOFT LIFE Kenya **AA**, MBOGI Kenya **C**, with PLUG as the everyday house blend — a deliberately local, grade-first naming scheme rather than estate names.
- The PLUG blend's product art (per their site) is "Roasted in Kenya" with a medium roast profile and chocolate/caramel/nutty tasting notes, marketing itself as "made for every cup".
- Beyond retail, the same building hosts the Nakuru Coffee Roasting School, offering a 4-week Certificate in Professional Coffee Roasting (KES 35,000) and shorter courses for farmers and cooperatives (KES 20,000–25,000).

## Scraping Quirks

- **Domain maze**: the checklist's `roastrepublik.co.ke` does not resolve; `roastrepublik.com` is an unrelated Indian multi-roaster marketplace, and `roastrepubliccoffee.com` belongs to a different "Roast Republic" brand. The real shop is **www.kenyan-coffee.com**, operated by Roast and Grind Africa Ltd (identity confirmed via the site's own structured data and the `roastrepublik@gmail.com` contact).
- An unlaunched, password-protected Shopify store exists at `roast-republik.myshopify.com` (its `products.json` redirects to the password page) — a dead end; the live storefront is Zoho Commerce.
- Zoho's `/categories/...` pages return **empty response bodies** to server-side fetches; the static `/shop-coffee` mega listing (all sections on one page) is used for discovery instead.
- Product URLs are opaque (`/products/<hash>/<numeric-id>`), so bean filtering runs on the listing card's product name, not the URL; wholesale café bags, roasting courses, mobile-bar experiences and brewing equipment are excluded by name.

## Sources

- https://www.kenyan-coffee.com/ (homepage, site structured data)
- https://www.kenyan-coffee.com/about-us
- https://www.kenyan-coffee.com/contact-us
- https://www.kenyan-coffee.com/green-coffee-sourcing
- https://www.kenyan-coffee.com/coffee-roasting-classes-in-kenya
- https://www.kenyan-coffee.com/shop-coffee
- https://www.kenyan-coffee.com/Shipping_and_Delivery.pdf
