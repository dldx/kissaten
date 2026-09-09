---
type: "Reference"
title: "94 Celcius — Roaster Profile"
description: "Science-driven Quebec roaster in Sainte-Julie (greater Montreal) — Probat P12 roasting, experimental co-ferments from producers like Wilton Benitez and Diego Samuel Bermúdez, and the #NeverBitterAlwaysFair motto."
---

# 94 Celcius — Roaster Profile

## Overview

94 Celcius is a specialty coffee roaster founded in 2017 by Marc-Alexandre Emond-Boisjoly and based in Sainte-Julie on the South Shore of Montreal, Quebec, Canada. The storefront is bilingual — French by default with an English locale at `/en/` — and sells single origins, espresso blends, experimental co-fermented lots, and a "Femmes Productrices" line alongside equipment, matcha/tea, and merch. The company also sells wholesale and reports being available in more than 250 points of sale (per their site); in 2026 it was named one of eight micro-roasters to watch at the Rabbit Hole Community Reviews Coffee (per their site).

## Address

- 1081B Rue Principale, Sainte-Julie, QC, Canada — roastery and roasting workshop; local pickup available Monday–Thursday 9:00–16:00 and Friday 9:00–12:00 (per their site).

## Roasting & Equipment

- Roasts on a Probat P12, described as an industry-reference drum roaster; each profile is developed with high-precision temperature probes for lot-to-lot consistency (per their FAQ).
- Founder Marc-Alexandre Emond-Boisjoly has a B.Sc. in biochemistry and an M.Sc. in pharmacology, with prior university research in autophagy, cell signalling, and molecular physiology — the roastery frames its approach as "science or coffee: the alliance that defines us" (per their site).

## Sourcing & Transparency

- Collaborates with innovative producers including Diego Samuel Bermúdez, Wilton Benitez, and Pepe Jijón, with fully traceable lots (per their site).
- Pricing tiering is explained on the FAQ: Classic coffees start around CAD 22–23 and Exceptional lots can exceed CAD 30–35; no FOB/farm-gate figures are published.

## Schedules & Shipping

- Free delivery in Canada on orders of CAD 35+ and to the USA on orders of USD 50+; orders ship within 24–72 business hours (per their FAQ).
- Canadian orders ship mainly via Canada Post, with GLS and UniUni used for some Quebec/Ontario deliveries; US orders ship via FedEx Express. Same-day delivery is available in the greater Montreal region for an extra fee.
- Carbon-neutral shipping on all orders (per product-page badge); in-stock orders can be ready for roastery pickup within 24 hours.

## Philosophy & Quirks

- Motto: **#JamaisAmerToujoursJuste** ("Never Bitter, Always Fair").
- Coffee series split into Classique, Exploratoire, and Exceptionnelle, alongside co-fermented and cold-brew lines; several blends carry the "Femmes Productrices" (women producers) tag.
- Several products have cryptic handles without coffee keywords (e.g. `papilles`, `momo24`, `oree`, `velvet`) — many of these are wholesale-only beans sold to cafés under their own names.

## Scraping Quirks

- The store is bilingual (French default, English at `/en/`); the scraper points at the **English-locale** `products.json` (`/en/collections/cafes/products.json`) so extracted content is already in English — no AI translation pass needed.
- The base scraper's URL filter drops any URL containing `surprise` (a mystery-box pattern), but 94 Celcius's "Surprise Trio" is a genuine three-bag coffee sampler; the scraper rescues it and flags it `is_tasting_kit` / `requires_review` so it flows through the tasting-kit review queue.
- `store_currency` is pinned to CAD because the store serves multiple Shopify Markets locales (`/en/`, `/en-us/`, `/en-jp/`); geo-detected currency must never override CAD.

## Sources

- https://94celcius.com/ (free-shipping banner, footer about text)
- https://94celcius.com/en/pages/a-propos (founder story, founding year, producer collaborations)
- https://94celcius.com/pages/faq (carriers, free-delivery thresholds, pickup address/hours, Probat P12, price tiers)
- https://94celcius.com/pages/nous-contacter (roastery address)
- https://94celcius.com/products/keramo-cafe-ethiopie-lave (carbon-neutral shipping badge)
