---
type: "Reference"
title: "Connect Coffee Roasters — Roaster Profile"
description: "Nairobi specialty roaster and B2B coffee company selling two signature blends (Romeo and Juliet) plus drip pouches, with direct sourcing from Kenyan partner farms and a Coffee Research Foundation partnership."
---

# Connect Coffee Roasters — Roaster Profile

## Overview

Connect Coffee Roasters (connectcoffeeroasters.net) is a specialty coffee
roaster and café company based in Nairobi, Kenya, running a Hostinger Website
Builder storefront with prices in Kenyan Shilling (KES). It operates as both a
consumer brand and a B2B business — green and roasted bean supply, coffee
equipment distribution and a coffee equipment showroom — with a café branch in
Karen (Nairobi) listed on the contact page. The roasted range centres on two
signature blends: Juliet (medium roast, fruity and floral) and Romeo (dark
roast, smoky dark chocolate and nutty), sold in 250g and 1kg bags, plus a
Barista Pouch of five 12g ground-coffee pouches.

## Address

- Nairobi, Kenya (full roastery street address not published on site; the
  site lists a Karen branch café and phone contacts only).

## Sourcing & Transparency

Per their site, beans are sourced directly from partner farms and selected
co-operatives, trading "for the common good of coffee communities" and
engaging farmers as business partners. They state they supply AA quality green
and roasted beans with cup scores over 85, and that customers get information
on the source of their coffee ("we are transparent and offer certified
processes through our supply chain"). No specific FOB or farm-gate price
figures are published.

## Sustainability

Per their Our Story page, Connect Coffee is committed to engaging and
assisting partner farmers to improve coffee production (quantity and quality)
and farmer welfare through:

- Provision of financial support for quality certified coffee seeds,
  fertilizers, and renovation of processing facilities.
- Training on best farm practices — pest and nutrition management, timely
  planting, and pruning.
- A partnership with the Coffee Research Foundation (CRF) for farmer training,
  research & development, and monitoring & evaluation.

## Philosophy & Quirks

- Tagline: "Experience specialty coffee through meaningful connections" — the
  connection theme runs through everything ("We believe in the value of
  connection", "Purpose beyond Profit", "Coffee with Integrity").
- The banner across the site says "our online shop is currently being set up
  to serve you better. In the meantime, please place your orders via call or
  Instagram DM" — yet the web shop is live and lists priced products.
- Romeo and Juliet blend naming: Juliet is the light/medium "morning" blend,
  Romeo the dark signature espresso blend.

## Scraping Quirks

- **Domain trap**: connectcoffeeroasters.com is a *different company* — a
  Macau-based "Connect Coffee Roasters" on a WordPress site. The Nairobi,
  Kenya roaster is at **connectcoffeeroasters.net**.
- Hostinger Website Builder storefront: no products.json; product discovery
  comes from `sitemap.xml` (product pages live at the domain root,
  `/<slug>`, not under `/shop/`). The `/shop` grid renders client-side, so
  sold-out state is read from each product page's JSON-LD
  `offers.availability`.
- Of ~88 sitemap product pages, all but a handful are barista equipment
  (espresso machines, grinders, kettles, filter papers) whose slugs often
  contain "coffee" (e.g. `hario-coffee-grinder`), so the scraper uses a
  coffee-keyword *include* filter on slugs rather than an exclusion list.
- The Juliet Blend 1kg product page currently shows a Romeo Blend bag photo —
  site image/name mismatch, so bean images may not match the blend name.
- The Barista Pouch (5 × 12g ground-coffee pouches) is a coffee product, not
  equipment; it flows through the normal pipeline and would be flagged into
  the admin review queue if the tasting-kit classifier matches it.

## Sources

- https://connectcoffeeroasters.net/
- https://connectcoffeeroasters.net/our-story
- https://connectcoffeeroasters.net/services
- https://connectcoffeeroasters.net/contact
- https://connectcoffeeroasters.net/roasted-coffee-beans-juliet-blend-1kg
- https://connectcoffeeroasters.net/specialty-coffee-blend
