---
type: "Operations"
title: "Tasting Kit Review Pipeline — 2026-08"
description: "How curated tasting kits/samplers went from silently excluded to scraped, flagged (is_tasting_kit / requires_review), and held out of public search until an admin approves them via page_feedback, apply-review-decisions, and diffjson promotion."
generated: { by: "openwiki/0.4.3", at: "2026-08-29T13:59:13.975Z" }
---

# Tasting Kit Review Pipeline

## Overview

Roasters sell curated multi-coffee products — taster packs, samplers, tasting
kits — alongside real beans. Historically the scrapers silently **excluded**
those (URL/name substring filters for `sample`, `taster-pack`, …), so they
never entered the database.

Since commit `6d5e1a8` the pipeline instead **extracts** kits, **flags** them,
and holds them **out of public search until a human reviews** them. Approved
kits get promoted into the public search view through a diffjson; rejected
ones stay hidden. Nothing is silently dropped and nothing unpublished leaks
into public search.

## The two flags

Both live on `CoffeeBean` (and `CoffeeBeanDiffUpdate` / `CoffeeBeanOptional`)
and in the DuckDB `coffee_beans` table.

| Flag | Type | Default | Meaning |
|---|---|---|---|
| `is_tasting_kit` | `bool` | `false` | **Persistent category flag.** Set by the AI extractor and/or a URL heuristic. Survives approval and stock-update diffs; powers the public "Sampling kits" search filter and bean-page chips. |
| `requires_review` | `bool` | `false` | **Gate flag.** Set at scrape time for brand-new kits. `true` rows are hidden from public search until an admin decides; approved rows flip to `false`. |

Interaction: `is_tasting_kit` is a hard equality filter (mirroring
`is_decaf`); `requires_review` is a *hidden-row gate* — public endpoints add
`WHERE requires_review = false` by default.

## Lifecycle

```
 scrape ──► flag ──► review ──► approve ──► diffjson ──► refresh ──► promote
  │         │          │          │            │            │           │
  │   is_tasting_kit  │           │            │   rebuilds rw DB    copy rw
  │   = true,         ▼           ▼            │   (recursive glob   → prod
  │   requires_review admin "Flagged for review"  picks up           duckdb
  ▼   = true (new)   submits     decision in        data/reviews/     + restart
  bean             decision     page_feedback     <date>/*.review.     serve
                                 approved →        diffjson flips
                                 requires_review   requires_review
                                 = false           = false in DuckDB
```

## Scraper flagging

Short version — details in [Scraping System: Tasting Kits, Flag, Don't Exclude](../scrapers/scraping-system.md):

- Kit exclusions (`sample`, `taster-pack`, …) removed from `BaseScraper` and
  ~75 per-roaster scrapers.
- AI extractor sets `is_tasting_kit` on curated multi-coffee kits (it does
  **not** set `requires_review`).
- `BaseScraper._apply_product_flags(bean, url, is_new=True)` ORs the URL
  heuristic into `is_tasting_kit` and sets `requires_review = is_tasting_kit`
  only for new products — stock-update diffs use `is_new=False` and never
  re-hide an approved kit.
- Since 2026-08 flagging also detects kits by **name** (`_bean_name_is_tasting_kit`),
  not just URL, and exposes a `postprocess_review_flags(bean, url)` hook for
  roaster-specific overrides. `_get_tasting_kit_url_patterns()` also gained
  `sample`, `taster`, `gift-box`, `giftbox`, `sample-box`, `cupping-box`.

## API contract

`src/kissaten/api/main.py`:

- `FilterParams` / search queries gain `is_tasting_kit`, `requires_review`, and
  `include_unreviewed` (default `false`). Exposed on both `/v1/search` and
  `/v1/search/by-paths`.
- Public lists default to `REVIEW_HIDDEN_SQL = "cb.requires_review = false"`
  (plus an `_SB` variant). `is_tasting_kit` is a hard filter; an explicit
  `requires_review` param is a hard filter too (the admin queue queries
  `requires_review=true`, which suppresses the default hide clause);
  `include_unreviewed=true` reveals hidden rows for admin views.
- Roaster detail list filters hidden rows unless `include_unreviewed`;
  bean-detail endpoints (`get_bean_by_slug`) select the flags but do **not**
  hide the row — a reviewer must be able to open a pending product.
- `/v1/stats` is untouched: review-flagged rows still count.

See [Backend API & Database — Review-Flag & Kit Search Contract](../api/backend-api.md)
for the full table of filter semantics.

**Stale-DB note**: after deploying the schema changes, the first scrape batch
rebuilds the rw DuckDB. Until a full `kissaten refresh` + `cp` + serve restart
happens, the running DuckDB is missing the new columns: search can error out —
run a full `kissaten refresh` (not just `--incremental`) after rollout.

## Admin review UI

`frontend/src/routes/(main)/admin/+page.svelte` — **Flagged for review**:

- Queue loads via `api.search({ requires_review: true, per_page: 50,
  sort_by: "date_added", sort_order: "desc" })` plus
  `listProductReviewDecisions()`.
- `pendingReviewItems` (queue items with no recorded decision) get Reject /
  Approve buttons; `decidedReviewItems` render as muted "Previously decided"
  cards with the decision badge, relative time, and allow re-review.
- Decisions are stored in `page_feedback` (`kind='product-review'`,
  `fields:[{key:'decision', value:'approved'|'rejected'}]`). `submitProductReview`
  dedupes: if the latest recorded decision for a path equals the submitted one,
  no duplicate row is inserted. `listProductReviewDecisions` (admin-only, built
  with `query(...)`, not `command`) returns the latest decision per
  `entity_url_path`.
- Link gotcha: card links are `"/roasters" + item.bean_url_path` because
  `bean_url_path` is stored **without** the `/roasters` prefix.

## `kissaten apply-review-decisions`

```
kissaten apply-review-decisions --from-db <path> [--data-dir data] [--dry-run] [--update-db]
```

- Reads `page_feedback` rows (`kind='product-review' AND status='new'`) from
  the frontend SQLite DB via stdlib `sqlite3` in read-only mode (`mode=ro`,
  with an `immutable=1` fallback for WAL/lock errors).
- Takes the **latest** decision per `entity_url_path` (rowid order, last
  wins).
- **Approved** → writes a `CoffeeBeanDiffUpdate` diffjson
  `{url, requires_review: false, scraped_at, scraper_version: "2.0"}` **next
  to the bean's own JSON** under `data/roasters/<roaster>/<session>/<slug>_<hash8>.review.diffjson`.
  `kissaten refresh` picks it up every run via the recursive glob
  `data/**/*.diffjson` (see `src/kissaten/api/db.py`), so the approval is
  durable across re-scrapes. Approved rows with no backing bean JSON are
  skipped (stay `new`, warning printed) so a later run can retry.
- **Rejected** → writes no diffjson (the item stays hidden: `requires_review`
  stays `true` in DuckDB) and marks the row applied.
- **`--update-db`** (non-dry-run only) additionally writes
  `requires_review = false` **directly into the rw DuckDB** for each approved
  bean, so approvals take effect before the next `kissaten refresh`. Best
  effort: if the rw DB cannot be opened, the diffjson files are still written
  and apply on the next refresh. Promotion (`cp` + serve restart) is still
  required for the API to serve the change.
- Idempotent: processed rows flip `status='applied'`; only `new` rows are
  re-read. `--dry-run` prints the table and writes/marks nothing. Outputs a
  rich Table summary and the `refresh` / `cp` promotion reminder.

### Entity-path matching

The bean lookup is keyed by both the product URL and the derived
`bean_url_path` **in both the timestamped and timestamp-stripped forms**
(`<slug>_<HHMMSS>` vs `<slug>`), because refreshes before timestamp-stripping
stored the raw suffix in `bean_url_path` while current refreshes store the
stripped form — the frontend's `entity_url_path` mirrors whichever form the DB
had when the decision was recorded. For product-URL lookups the **newest
session folder wins** (session folder names are ISO timestamps, so string
comparison equals chronological order), mirroring how scraper-produced diffs
land next to the current bean JSON. A relaxed match strips any trailing
`_<HHMMSS>` from the entity path before retrying.

## Promotion steps

1. `kissaten refresh` (or `--incremental`) — rebuilds/updates the rw DuckDB.
2. `cp data/rw_kissaten.duckdb data/kissaten.duckdb` — publish.
3. Restart `kissaten serve` so the API reads the new file.

## Gotchas

- **DuckDB `ALTER TABLE… ADD COLUMN … DEFAULT FALSE` aborts the whole
  transaction on failure** — the migration therefore does a `DESCRIBE
  coffee_beans` existence check *before* the `ALTER`, so a missing column
  migration never nukes the batch.
- **`coffee_beans_with_categorized_notes` view**: the explicit `GROUP BY`
  must list both `is_tasting_kit` and `requires_review` or DuckDB fails with
  "must appear in GROUP BY" — both columns are in the list by design.
- **First scrape wave**: the first scrape after rollout re-extracts kits that
  were previously excluded, producing a large initial review queue.
- **`sample` in legit product names** (e.g. a "sample roast") also lands in
  the review queue — by design, better to flag a doubtful product than to
  silently drop it or leak it into public search.

## Cross-links

- [`docs/KIT_REVIEW.md`](../../docs/KIT_REVIEW.md) — project reference for the
  same pipeline (lifecycle, flags, CLI details).
- [Tasting Kit Flagging & Review Pipeline — 2026-08 (original plan)](tasting-kit-review-plan-2026-08.md).
- [Scraping System — Tasting Kits: Flag, Don't Exclude](../scrapers/scraping-system.md).
