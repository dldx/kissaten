---
type: "Reference"
title: "Delicate Coffee — Roaster Profile"
description: "Chicago two-person micro-roastery (\"an artist and a roaster\") selling seasonal 125 g single-origin lots with unusually long producer and co-op write-ups."
---

# Delicate Coffee — Roaster Profile

## Overview

Delicate Coffee Roasters is a Chicago micro-roastery described on its own site as "a team of two: an artist and a roaster". The current catalogue is a small, tightly edited set of single-origin lots — the site says "We can't wait to see your POVs" on the love of single origin coffees — sold as a standard 125 g whole-bean bag. Release naming is spare and lot-based, with grading or preparation suffixes such as `getuya AA`, `kii peaberry`, `halo beriti – special prep` and `kathima AB – rested`. Unlike most roasters this one leads with long producer write-ups on every product page (Taste, Processing, and a section on the producing family or factory), and the bag and product presentation leans into the roaster's own artwork. There is no blend, no gear, no subscription and no gift card in the current catalogue.

## Address

- delicate coffee roasters, 1001 N. North Branch Street, Unit 301, Chicago, Illinois 60642, United States. (The terms page renders it as "1001 N. North Branch | Unit 301 | Chicago, IL 60642".)

## Roasting & Equipment

- Roast intent per the site: "Our target roast aims to highlight acidity at the forefront and showcase any other flavors within each bean, from fruit to florals."
- No roasting-machine brand or model is published on the site.

## Schedules & Shipping

- "We plan to release new beans seasonally" — there is no fixed weekly roast day.
- Rested product is an explicit option: "rested coffee ! these bags have been roasted ahead of time so you don't have to wait." Listings are suffixed `(rested)`.
- Free shipping is quantity-based rather than value-based: "Enjoy free shipping on any order that includes the purchase of two or more bags" (repeated in the site header as "free shipping when you grab 2 or more bags").
- "Orders are fulfilled within 2 weeks of purchase." Carrier: "All orders are shipped via USPS Ground Shipping."
- US only: "We currently ship within the United States only." No international shipping.

## Sourcing & Transparency

- Lots are attributed to named importers rather than to a stated direct relationship — e.g. "Sourced from Swift Coffee Sourcing" on `bare – special prep` and "Sourced from Cafe Imports" on `halo beriti – special prep`. The site does not explicitly claim direct trade, and publishes no price transparency (no FOB, farm-gate or percentage-of-retail figures).
- Product pages do carry concrete co-op/factory membership figures, which is the most producer-facing content on the site: Kii Factory / Rungeto Farmers Cooperative Society, ~1,215 active farmer members; Kathima Factory / Thambana Farmers Cooperative Society, ~4,500 supported farmers; Getuya Factory / New Murarandia Farmers Cooperative Society, ~3,500 smallholder members.
- Some pages describe producer-level environmental work — e.g. the Gachatha listing notes "soak pits for water treatment to avoid contamination with fresh-water sources" and preserving indigenous plant life "to protect local bird and animal species". Attribute this to the producing co-op or factory, not to Delicate Coffee as a company.
- No sustainability programme or certification is published by the roaster itself.

## Philosophy & Quirks

- Positioning statement: "For us, protecting our craft means sharing it, so we're committed to nourishing our communities by sharing art, supporting creators, and building connections over a cup of coffee."
- The roaster is an artist: the archive contains four retired "coffee bud prints", numbered `print 1`–`print 4` — art releases tied to coffee releases.
- No founding year and no awards are published on the site.

## Scraping Quirks

- **Retired art prints share the product space.** `print 1`–`print 4` are not beans. They live in their own `prints` collection but still appear in the broader product sitemap, so a scraper working from all-products rather than the curated `shop` collection must exclude them explicitly.
- `product_type` and `tags` are empty on every current product — all filtering has to be by slug and title.
- Three collections (`frontpage`, `garage-sale`, `shop`) all render the same current selection despite their names; only `archive` is genuinely historical. Don't trust collection names as an indication of what's in them.
- Coffee data lives entirely in `body_html` as labelled lines (`From :`, `Varietal :`, `Process :`, `Notes :`) plus prose sections — there are no structured metafields.

## Sources

- https://delicate.coffee
- https://delicate.coffee/collections/shop
- https://delicate.coffee/policies/shipping-policy
- https://delicate.coffee/policies/contact-information
- https://delicate.coffee/policies/legal-notice
- https://delicate.coffee/products/bare-special-prep
- https://delicate.coffee/products/gachatha-ab
- https://delicate.coffee/collections/prints