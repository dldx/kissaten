---
type: "Reference"
title: "Roaster Profile — Template & Conventions"
description: "The template for one-page roaster profiles in openwiki/roasters/: frontmatter, section order (Overview → Address → sustainability/sourcing/equipment/shipping/philosophy → Scraping Quirks → Sources), what to capture (roastery address only, roasting machine, roast & dispatch schedules, per-region shipping rates, free-delivery minimums, sourcing price transparency, producer-benefiting initiatives) and grounding rules."
---

# Roaster Profile — Template & Conventions

Every roaster in Kissaten's catalogue that has a working scraper gets one
profile page in `openwiki/roasters/`. The format is **global** — the same
here for UK, Europe, Asia, the Americas — so keep it generic and grounded in
verified facts.

## Frontmatter

```yaml
---
type: "Reference"
title: "<Roaster Name> — Roaster Profile"
description: "<one-line summary of what makes this roaster distinctive — location, a signature fact or two, notable products>"
---
```

- `title` uses the roaster's proper display name, not the registry key.
- The `description` should tempt a reader: location + the most interesting
  1-2 facts (e.g. "Glenfiddich Spirit of Scotland Award 2012 and a Taster
  Pack kit").
- Filename: `<registry-key>.md` (e.g. `bells-beans.md`, `artisan-roast.md`).

## Required section (always first after the H1)

```
## Overview
```

2-5 sentences: who they are, where (city/country), what the storefront is
(Shopify / WooCommerce / Squarespace / Wix …), and the headline facts —
founding year, signature blends/origins, notable products.

```
## Address
```

- Only the **roastery** address — the location where the coffee is roasted
  (and usually dispatched from). Café, store and retail-storefront addresses
  do **NOT** belong here; if the roaster operates cafés, mention them in the
  Overview instead.
- One bullet for the roastery address: street (if published), town, region,
  postcode, country. **Always include the country.**
- If only city+country is known, give that and state “full address not
  published on site”.
- For global roasters list the home-country roastery and note further
  outposts in the Overview instead.

## Optional sections (include only when there is real, verified content)

Order: **Sustainability**, **Sourcing & Transparency**, **Roasting &
Equipment**, **Schedules & Shipping**, **Philosophy & Quirks**.

| Section | Content |
|---|---|
| `## Sustainability` | Concrete initiatives only: reusable packaging, chaff composting, direct trade / certifications, Reforestation / One Tree Planted, electric fleet, etc. Skip if the site publishes nothing. |
| `## Sourcing & Transparency` | Price transparency — FOB price per kg, farm-gate / price-paid-to-producer figures, volume purchased, importer names, cost-breakdown pages — and ethical sourcing signals: direct trade, organic/fairtrade/RFA/UTZ certifications, co-op or producer-association memberships, worker-run co-ops, charitable or community giving programmes. |
| `## Roasting & Equipment` | Actual hardware and method — the roasting machine used (brand + model, e.g. Giesen W6, Probat, Loring S35, capacity if published), hot-air roasting, roasting software (Cropster), open-to-view roastery, QC cupping rituals. |
| `## Schedules & Shipping` | Roasting cadence (e.g. "roasted weekly", "roasted to order", "roasted on Mondays"), dispatch days and delivery timeframes, the **minimum order value for free delivery** (amount + currency, e.g. "free UK delivery over £20"), and — only if the site presents it — country/region-specific shipping rates or free-delivery thresholds (amount + currency per region). |
| `## Philosophy & Quirks` | What makes the roaster distinctive beyond the basics: motto/tagline, naming quirks (e.g. sampler packs named Eeny-Meeny-Miny-Moe), founders' story, award history, “nothing wasted” circularity. |

Optional section order is **Philosophy & Quirks last** before Scraping Quirks.

## What to look for (optional sections)

### Sustainability

Research the about / sustainability / sourcing pages for concrete, verifiable
initiatives only: reusable or recyclable packaging, chaff composting,
reforestation programmes (e.g. One Tree Planted), electric fleets, water
reuse. Also capture initiatives that directly benefit coffee producers —
e.g. a fixed amount reinvested per bag or pound sold, producer medical or
education grants, conservation or infrastructure projects with partner
farms. If the site publishes nothing concrete, omit the whole section
(do not guess).

### Sourcing & Transparency

When the roaster publishes price-transparency data — FOB price per kg,
farm-gate or price-paid-to-producer figures, importer names, volume
purchased, or a dedicated transparency/cost-breakdown page — record the
concrete numbers and where they appear (per-product page vs. a standalone
transparency page). Also capture ethical sourcing signals: direct trade,
organic/fairtrade/RFA/UTZ certifications, producer co-op or association
memberships, worker-run co-operatives, and charitable or community giving
programmes — including initiatives that directly benefit coffee producers
(e.g. a fixed amount reinvested per bag or pound sold, producer medical or
education grants, conservation projects with partner farms). If nothing is
published, omit the whole section (do not guess).

### Roasting & Equipment

Research the roasting machine used — check the about, roastery and
company-history pages for brand, model, capacity and upgrade history
(e.g. "Loring S15 Falcon, upgraded to a Loring S35 in autumn 2024"). Also
record the roasting method (drum vs hot-air), roasting software (Cropster),
and QC practices (cupping rituals, open-to-view roastery). Omit the section
if the site publishes no hardware or method details.

### Schedules & Shipping

Record what the roaster publishes about fulfilment — typically on a shipping
policy, FAQ, checkout banner or footer page:

- Roasting cadence (e.g. "roasted weekly", "roasted to order", "roasted on
  Mondays").
- Dispatch days and delivery timeframes (e.g. "dispatched Tue/Thu",
  "1st class, 2–3 days").
- Free-delivery threshold: the **minimum order value** that unlocks free
  shipping (amount + currency).
- Country/region shipping rates — **only if the site presents them**: when a
  shipping policy lists rates or free-delivery thresholds per destination
  country or region (e.g. "free from EUR 40 in Germany, from EUR 75 across
  Europe"), record each tier with amount + currency + region. Do not infer
  rates for regions the site does not list.

If the site publishes none of this, omit the section.

## Scraping Quirks (only if there is a genuine quirk)

Was **`## Scraping Notes`** — boilerplate (registry name, platform type, shop
URLs, currency, bean counts) does **NOT** belong in a profile page. Rename it
`## Scraping Quirks` and keep **only** facts that would trip up a future
contributor, e.g.:

- Domain corrections (checklist domain dead → real shop, marketplace vendor →
  real brand shop)
- Stores of different companies sharing a name (e.g. UK “Asylum Coffee” vs
  Singapore “Asylum Coffeehouse”)
- Scraper filters that change what lands in the catalogue (mixed-store coffee
  include filters, wholesale `-office`/`-3kg` dedup, empty category archives)
- Tasting-kit products that must flow through the review queue (flag
  `is_tasting_kit` / `requires_review`), never excluded

If a roaster has no such quirks, omit the whole section.

## Sources

Always end with:

```
## Sources

- <url>
- <url>
```

List the pages the facts were taken from (shop home, /about, sustainability
page, an origin page). Keep them verified; when in doubt, phrase the claim
“per their site”.

## Grounding rules

- **Never invent facts.** Only include what was verified on the site or in a
  reputable source; mark uncertainty with “per their site”.
- **Addresses must include the country** — mandatory for the global rollout.
  Only the roastery address belongs in `## Address`, not café/storefront
  locations.
- **Schedules, shipping and transparency**: when a roaster publishes roast /
  dispatch schedules, a free-delivery minimum, per-country/region shipping
  rates, or price-transparency / ethics data, record the concrete details
  (amounts + currency, day names, regions) exactly as presented; when it
  publishes none of these, omit the detail (or the whole section) rather than
  guessing.
- **No scraping boilerplate** (registry name, platform, currency, bean counts,
  shop URLs) — those live in the scraper code and `scraping-system.md`.
- Flag-things: any product that flows through the tasting-kit review queue
  should be called out in Scraping Quirks.
- Keep pages short; a good profile is a sprint, not a marathon: ~1 printed
  page of useful facts.

## Cross-links

- [Index](index.md) — the discovery page for all profiles.
- [Scraping System](../scrapers/scraping-system.md)
- [Tasting Kit Review Pipeline](../operations/tasting-kit-review-pipeline.md)