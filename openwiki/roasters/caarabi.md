---
type: "Reference"
title: "Caarabi Coffee Roasters — Roaster Profile"
description: "New Delhi roastery whose name is an anagram of Arabica — estate-partnered Indian single origins, barrel-aged 'Spirit Series' lots, and India's first Coffee Omakase experience."
---

# Caarabi Coffee Roasters — Roaster Profile

## Overview

Caarabi Coffee Roasters is a specialty coffee roastery in New Delhi, India
(legal entity: Caarabi Coffee Pvt Ltd). Its Shopify storefront at
caarabicoffee.com sells single origins from named Indian estates, specialty
blends, a Dark Roast Series and barrel-aged "Spirit Series" lots, alongside
equipment and merchandise. It was founded in 2023 by two friends, Shubham
("the curious one") and AJ ("the coffee guy"), who brings Australian coffee
training; the site's earliest store listings date to mid-2023. Beyond the
shop, Caarabi runs India's first "Coffee Omakase" tasting experience, is the
coffee partner of Delhi's Altogether Experimental spaces, and co-runs the
Indiroom café in Goa with Chef Kunal Kapur.

## Address

- Plot no 02, Khasra 264, Butterfly Park, Said Ul Ajaib, New Delhi 110030 — India (roastery and retail space, open Wednesday–Sunday 09:00–18:00)

## Sourcing & Transparency

- The site publishes no price-transparency figures, but names its estate partners on a dedicated "Our Estate Partners" page: **Attikan Estate** (Biligiri Rangan Hills, est. 1890, up to 1,650 MASL), **Melkodige Estate** (Kudremukh, Western Ghats, 4,000 ft, run by horticulturist couple Aveen and Yogitha Rodrigue), and **Ratnagiri Estate** (Bababudangiri, est. 1927, shade-grown within a designated tiger reserve, stewarded by the family of founder Patre K. Shivappaiya, exporting since 1994). The footer also cites Karadykan and Baarbara among "named farms".
- Current single origins include Baarbara (Chikmagalur, Karnataka), Ratnagiri Washed AAA, Peren (Nagaland), Kangra (Himachal Pradesh), Odisha Yellow Honey and Kumergode, plus Global Drop lots from Nepal and Thailand.

## Schedules & Shipping

- **Roast to order**: shipped Monday–Friday, pickup within 1–3 business days; orders placed after 8 am IST on Fridays roast and ship the following Monday. Typical delivery window is 3–6 business days.
- Free standard shipping (Delhivery/Bluedart, 2–5 business days) on orders of **INR 1,000 or more**; expedited Bluedart Next Day / Delhivery Express available at checkout.

## Philosophy & Quirks

- "Caarabi" is an anagram of **Arabica** — the about page spells it out as "Ca-arabi / Arabi-ca".
- Tagline: "Damn good coffee. Roasted with intent." The homepage claims every batch is cupped within 24 hours of roasting and that no batch "skips the table".
- The **Coffee Omakase** page bills the experience as "India's first Coffee Omakase" — a multi-course, reservation-only coffee tasting hosted by AJ, brewed fresh in front of guests and paired with food.

## Scraping Quirks

- The scraper reads the curated `shop-coffee-online` collection (~18 products, coffee only) rather than `all`, so equipment/merch collections are never seen; an insurance `exclude_slugs` list also blocks subscriptions, gift cards, gear and the `omakase` experience product.
- The store is pinned to INR: Shopify Markets can serve geolocated currency conversions to datacenter IPs, but every price on this store is INR.
- Product URLs are canonicalised from `/collections/<handle>/products/<slug>` to `/products/<slug>` to match the site's rel=canonical form.

## Sources

- https://caarabicoffee.com
- https://caarabicoffee.com/pages/aboutus
- https://caarabicoffee.com/pages/contact-us
- https://caarabicoffee.com/pages/our-estate-partners
- https://caarabicoffee.com/pages/the-roastery-1
- https://caarabicoffee.com/pages/experiences
- https://caarabicoffee.com/pages/ate
- https://caarabicoffee.com/pages/indiroom
- https://caarabicoffee.com/policies/shipping-policy
