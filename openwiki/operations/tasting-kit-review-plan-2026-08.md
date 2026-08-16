---
type: "Plan"
title: "Tasting Kit Flagging & Review Pipeline — 2026-08"
description: "Plan to add is_tasting_kit + requires_review flags across all scrapers, extract sampling/tasting kits instead of excluding them, review them in the frontend admin via page_feedback, and promote approved kits into the DuckDB search view via diffjson."
---

# Tasting Kit Flagging & Review Pipeline — 2026-08

## Background

Skylark Coffee sells curated tasting kits (Fermentation Project Tasting Set from James
Hoffmann & Lucia Solis, Gesha taster pack, co-ferment taster pack, Bette Buna process
taster pack) plus a generic four-pack sampler. The base class `is_coffee_product_url()`
substring-excludes `"sample"` and `"taster-pack"` (base.py `_get_excluded_url_patterns`),
so all of these were silently dropped before AI extraction — including legitimate,
desirable products like the Fermentation Project Tasting Set.

Instead of allow-listing specific URLs, we flip the model: **extract all kit-type
products, flag them as unreviewed, hide them from public search, review them in the
frontend admin (decisions logged in `page_feedback`), and let a later-stage CLI write
diffjson updates that promote approved kits into the DuckDB search view.** No direct
DuckDB ↔ frontend SQLite connection is needed.

## Design: two orthogonal flags on `CoffeeBean`

| Flag | Type | Meaning | Cleared by |
|---|---|---|---|
| `is_tasting_kit` | `bool = False` | Persistent category. AI-detected and/or URL-heuristic. Survives approval; powers a public "sampling kits" search filter and a bean-page chip. | Never (auto-set at scrape) |
| `requires_review` | `bool = False` | Temporary moderation gate. Extensible to future product types. Set at scrape time for kits (and future flagged types); `IS_TRUE` rows are hidden from search. | Admin approval → diffjson flips it to `false` |

Search hides `requires_review=true` rows by default; an `include_unreviewed` (admin)
param reveals them. Approved kits keep `is_tasting_kit=true` and become visible.

## Phase 1 — Schema, extractor, DB

- `src/kissaten/schemas/coffee_bean.py`: add `is_tasting_kit: bool = False` and
  `requires_review: bool = False` to `CoffeeBean` (l.360) and `CoffeeBeanDiffUpdate`
  (l.86) so reviews can flip them.
- `src/kissaten/ai/extractor.py`: system prompt (l.80–165) gains an `is_tasting_kit`
  field: "true when the page is a curated multi-coffee tasting kit/sampler/set
  (e.g. 'Fermentation Project Tasting Set'), even if each sub-coffee has an origin
  story. False for single products and for equipment/merch."
- `src/kissaten/api/db.py`:
  - DDL `is_tasting_kit BOOLEAN DEFAULT FALSE`, `requires_review BOOLEAN DEFAULT FALSE`
    (l.869–897).
  - `ALTER TABLE… ADD COLUMN` migrations beside the existing `price_usd` one (l.907–910).
  - Column lists in INSERT (l.2200) + response SELECTs (l.2142/2536/2918).
  - diffjson→column mapping in `apply_diffjson_updates` (l.1382).
- `src/kissaten/api/main.py`:
  - `FilterParams` (l.133): `is_tasting_kit: bool | None` public filter;
    `include_unreviewed: bool = False` (admin). When false → hard condition
    `cb.requires_review = false` added in the same spot as `in_stock_only`
    (l.570–573) and in all duplicate list builders (l.1509–1668 region, 2152, 2546,
    2918) via a shared module-level clause so future endpoints can't forget it.
  - Stats untouched (behaves as before; review-flagged rows still counted by /stats).

## Phase 2 — Scraper rollout (all scrapers)

- `src/kissaten/scrapers/base.py`:
  - Remove `"sample"`/`"taster-pack"` from `_get_excluded_url_patterns()` (l.1407)
    and `"taster-pack"` from `_get_excluded_product_name_categories()` (l.1575).
  - New hook `_get_tasting_kit_url_patterns()` default
    `["taster-pack", "sample", "sampler", "tasting-set", "tasting-kit"]` and helper
    `is_tasting_kit_url(url)`.
  - New `_apply_product_flags(bean, url)` called after AI extraction (l.1730) and in
    the Shopify JSON path (`shopify_base.py:239`): sets
    `bean.is_tasting_kit = bean.is_tasting_kit or self.is_tasting_kit_url(url)`;
    **only for new products** set `bean.requires_review = bean.is_tasting_kit`.
- Migrate per-roaster token overrides (~56 scrapers): strip `sampler`, `taster-pack`,
  `sample`, `sample-pack`, `sample-box`, `tasting-kit` tokens from
  `_get_excluded_url_patterns()` / `_get_excluded_product_name_categories()`
  overrides so kits flow through; keep non-kit tokens (grinder, v60, capsule,
  subscription, merch…).
  Inline cases (`manhattan_coffee.py:164` `tasting-kit` skip etc.) converted to
  flag-pass-through. Skylark drops its now-redundant `four-pack-sampler-mixed` path
  override; `12-days-of-christmas` stays excluded.
- Safety net: any miscategorized product simply lands in the review queue (hidden) —
  no data pollution.

## Phase 3 — Frontend

- `frontend/src/lib/api.ts`: `CoffeeBean` gains `is_tasting_kit?: boolean`,
  `requires_review?: boolean`; search accepts `isTastingKit` + `includeUnreviewed`.
- Admin: "Flagged for review" section in
  `frontend/src/routes/(main)/admin/+page.svelte` — lists `includeUnreviewed=true`
  products (image, name, roaster, price, source URL), Approve / Reject buttons,
  "already reviewed" state.
- `frontend/src/lib/api/feedback.remote.ts`: `submitProductReview(urlPath, decision,
  name, roaster)` inserts into `page_feedback`: kind `"product-review"`,
  `entityUrlPath/Slug/Name`, `fields: [{key:"decision", value:"approved"|"rejected"}]`,
  `status: "new"` (fields presence bypasses the 20-char message rule).
- Search UI: "Sampling kits" filter chip → `isTastingKit=true`; bean page shows a
  "Tasting kit" chip.

## Phase 4 — Promotion CLI

- `src/kissaten/cli/main.py`: `kissaten apply-review-decisions --from-db <path>
  [--dry-run]`:
  - Reads `page_feedback kind='product-review'`, takes the latest decision per
    `entityUrlPath`.
  - Approved → write `CoffeeBeanDiffUpdate {url, requires_review:false}` diffjson
    into `data/reviews/<YYYY-MM-DD>/`; refresh applies it every run (recursive
    `**/*.diffjson` glob, db.py:1296) — durable across re-scrapes.
  - Marks feedback row `status='applied'`; idempotent; rich summary; prints the
    existing `refresh` / `cp` reminder.
  - Multi-host: the `<path>` is a required CLI arg (single-host assumption on
    `frontend/local.db` is intentionally avoided).

## Phase 5 — Tests + docs

- Tests: schema validation; extractor prompt smoke; base scraper URL-flag logic
  (kit URL → included + flagged; equipment still excluded); API hidden/unreviewed
  visible / `is_tasting_kit` filter; CLI dry-run + diffjson emission.
- `docs/KIT_REVIEW.md` lifecycle (scrape → flag → review → approve → diffjson →
  refresh → promote); AGENTS.md schema notes + "When Modifying Schemas" checklist.

## Open considerations

- `"sample"` also appears in legit product names ("sample roast") — they will simply
  land in review queue. Acceptable by design (review-gate).
- One-time AI cost when previously-excluded kits are first scraped (~54 roasters).
- Approved kits keep `is_tasting_kit=true`; the flag does not mean "needs approval".
