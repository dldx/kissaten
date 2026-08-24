---
type: "Reference"
title: "Roaster Profile — Template & Conventions"
description: "The template for one-page roaster profiles in openwiki/roasters/: frontmatter, section order (Overview → Address → sustainability/sourcing/shipping/equipment/philosophy → Scraping Quirks → Sources), what to capture (incl. roast & dispatch schedules, free-delivery minimums, sourcing price transparency, ethical considerations) and grounding rules."
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

- One bullet per verified physical location: street (if published), town,
  region, postcode, country. **Always include the country.**
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
| `## Roasting & Equipment` | Actual hardware and method — Giesen, Diedrich, hot-air roasting, roasting software (Cropster), open-to-view roastery, QC cupping rituals. |
| `## Schedules & Shipping` | Roasting cadence (e.g. "roasted weekly", "roasted to order", "roasted on Mondays"), dispatch days and delivery timeframes, and the **minimum order value for free delivery** (amount + currency, e.g. "free UK delivery over £20"). |
| `## Philosophy & Quirks` | What makes the roaster distinctive beyond the basics: motto/tagline, naming quirks (e.g. sampler packs named Eeny-Meeny-Miny-Moe), founders' story, award history, “nothing wasted” circularity. |

Optional section order is **Philosophy & Quirks last** before Scraping Quirks.

## What to look for (new optional sections)

### Sourcing & Transparency

When the roaster publishes price-transparency data — FOB price per kg,
farm-gate or price-paid-to-producer figures, importer names, volume
purchased, or a dedicated transparency/cost-breakdown page — record the
concrete numbers and where they appear (per-product page vs. a standalone
transparency page). Also capture ethical sourcing signals: direct trade,
organic/fairtrade/RFA/UTZ certifications, producer co-op or association
memberships, worker-run co-operatives, and charitable or community giving
programmes. If nothing is published, omit the whole section (do not guess).

### Schedules & Shipping

Record what the roaster publishes about fulfilment — typically on a shipping
policy, FAQ, checkout banner or footer page:

- Roasting cadence (e.g. "roasted weekly", "roasted to order", "roasted on
  Mondays").
- Dispatch days and delivery timeframes (e.g. "dispatched Tue/Thu",
  "1st class, 2–3 days").
- Free-delivery threshold: the **minimum order value** that unlocks free
  shipping (amount + currency).

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
- **Schedules, shipping and transparency**: when a roaster publishes roast /
  dispatch schedules, a free-delivery minimum, or price-transparency / ethics
  data, record the concrete details (amounts + currency, day names); when it
  publishes none of these, omit the section rather than guessing.
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