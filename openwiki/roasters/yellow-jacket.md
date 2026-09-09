---
type: "Reference"
title: "Yellow Jacket Coffee — Roaster Profile"
description: "Cape Town (Kenilworth) roaster voted CMA Roastery of the Year 2024, with a rotating bench of African and Latin American single origins and the house blends Komodo and Circus Bear."
---

# Yellow Jacket Coffee — Roaster Profile

## Overview

Yellow Jacket Coffee is a South African specialty coffee roaster whose
roastery sits in Kenilworth, Cape Town. Per their site, the company has "10+
years experience" and was voted CMA (Coffee Magazine Awards) Best Packaging
in 2023 and Roastery of the Year in 2024. The Shopify storefront rotates a
large bench of single origins from across Africa and Latin America (Ethiopia,
Kenya, Burundi, Uganda, Rwanda, Colombia, Brazil, Costa Rica, El Salvador)
alongside the house blends Komodo and Circus Bear (250g and 1kg) and a 5-pack
of filter drip bags. Cupping events at the roastery are promoted on the site.

## Address

- 46 Goldbourne Road, Kenilworth, Cape Town, South Africa (roastery — visits
  invited per the site footer)

## Sustainability

- The site names "quality, sustainability, and the communities we serve" as
  commitments (about page), but publishes no concrete initiatives — no
  verified programme details.

## Schedules & Shipping

- Free shipping on orders above R600 throughout South Africa (site banner);
  no roast/dispatch cadence is published.

## Philosophy & Quirks

- Roastery-first, retail-second presentation: the footer invites visitors to
  the Kenilworth roastery and the blog promotes cupping sessions there.
- Award-led branding ("Voted roastery of the year 2024" on the homepage).

## Scraping Quirks

- No single curated collection covers the bean line-up: `new-releases` holds
  the single origins but misses the house blends (Komodo, Circus Bear), so
  the scraper uses `collections/all` with an `exclude_slugs` net for the
  equipment items (espresso scale, V60s, barista cloths, filter holders,
  Third Wave Water sachets).
- Collection-prefixed product URLs 301-redirect to the canonical
  `/products/<handle>` form; the scraper strips the collection segment up
  front.
- The Filter Drip Pack is kept: it is coffee, and if the AI extractor
  recognises it as a tasting kit it flows through the review queue
  (`is_tasting_kit` / `requires_review`) rather than being excluded.
- Shopify handles can contradict titles (`ethiopia-chelbesa-red-honey` is
  titled "Rwanda - Vunga - Natural") — extraction must follow page content.
- Store currency is pinned to ZAR with `Accept-Language` removed so Shopify
  Markets geo-conversion cannot re-stamp prices for a datacenter IP.

## Sources

- https://yellowjacketcoffee.co.za
- https://yellowjacketcoffee.co.za/pages/about
- https://yellowjacketcoffee.co.za/pages/contact
- https://yellowjacketcoffee.co.za/collections/all
