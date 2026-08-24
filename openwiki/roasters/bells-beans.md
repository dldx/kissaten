---
type: "Reference"
title: "Bell's Beans — Roaster Profile"
description: "Woking 'nano roastery' built from a love of engineering and consistency — Eeny-Meeny-Miny-Moe sampler packs, 'Coffee Coffee' vs 'Funky' categories, and the Solis & Hoffmann Fermentation Project."
---

# Bell's Beans — Roaster Profile

## Overview

Bell's Beans is a Woking, Surrey roastery describing itself as "a purpose-built
speciality coffee **nano roastery**". The self-description is as good a profile as
any: "One roaster, one drum, a lot of cupping spoons." It is a Shopify storefront
at [bellsbeans.co.uk](https://bellsbeans.co.uk).

## Address

- Woking, Surrey — United Kingdom (a micro-roastery rather than a street
  address; full address not published on the site)

## Roasting & Equipment

- One small drum roaster — the "nano" scale is the whole point.
- Light-to-medium roast philosophy.
- Builds are grounded in "a love of engineering and the pursuit of
  consistency" — the equipment is one half of that pursuit, and cupping is the
  other.

## Philosophy & Quirks

- Self-aware and unpolished by design: "I'm not fancy, polished or even
  professional sometimes and I don't apologise for that, I just focus on roasting
  really really great coffee."
- Sampler packs are named after the nursery rhyme — **Eeny, Meeny, Miny, Moe**
  (URLs `sample-eeny`, `sample-meeny`, `sample-miny`, `sample-pack-moe`, plus
  `sample-pack-natty`).
- Categories coffees as "**Coffee Coffee**" (chocolate/nut classics) vs
  "**Funky coffees**" (fermented/natural/anaerobic).
- Sells **The Fermentation Project by Lucia Solis & James Hoffmann** — a notable
  collaboration kit (4×100g, one bag per process), flagged
  `is_tasting_kit`/`requires_review` for the review queue; see the
  [scraping-system tasting-kit policy](../scrapers/scraping-system.md).
- Notable beans: Peru Finca Los Orquídeas Winkler Tapia Geisha nanolot, Brazil
  Patricia (volcanic fermentation, Mundo Novo), Myanmar Khar Taw Hmi Geisha.
- Free delivery over £30; free delivery in GU21/GU22.

## Scraping Quirks

- **Empty curated collection**: the site's curated coffee collection is empty,
  so the scraper fetches the **whole catalogue** from the root `products.json`
  and filters locally.
- **Sampler packs are deliberately NOT excluded** — the Eeny/Meeny/Miny/Moe
  sampler packs flow through and are flagged `is_tasting_kit` / `requires_review`,
  landing in the admin review queue (see the
  [scraping-system tasting-kit policy](../scrapers/scraping-system.md)).

## Sources

- https://bellsbeans.co.uk/
- https://bellsbeans.co.uk/pages/about
- https://bellsbeans.co.uk/collections/sample-packs