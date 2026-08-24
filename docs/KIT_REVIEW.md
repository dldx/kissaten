# Tasting-Kit Review Pipeline

Curated tasting kits and samplers — products that bundle multiple coffees into
one "taster pack", "sampler", or "tasting kit" — are not coffee beans, but they
often sit alongside real beans on a roaster's storefront. Historically the
scrapers simply **excluded** these products so they never entered the database.
That silently dropped them from the catalogue.

Today the pipeline instead **extracts** kits, **flags** them, and holds them
**out of public search until a human reviews** them. This doc explains the
lifecycle, the two flags, how admins review, and how decisions reach the
database.

## Lifecycle

```
 scrape ──► flag ──► review ──► approve ──► diffjson ──► refresh ──► promote
  │         │         │          │            │            │           │
  │    is_tasting_kit  │          │            │     rebuilds rw DB   copy rw → prod
  │    = true          │          │            │     from JSON+diffjson
  ▼         ▼          ▼          ▼            ▼            ▼
 bean  requires_review public search   admin      data/roasters/ duckdb gets
       = true         hides bean      picks      <roaster>/      requires_review
                                       approve/   <session>/     = false → visible
                                       reject     <slug>_.review.
                                                 diffjson
```

1. **Scrape** — `BaseScraper` (and the Shopify base path) detects a tasting-kit
   URL via `is_tasting_kit_url()` and calls `_apply_product_flags(bean, url,
   is_new=True)`. The AI extractor also sets `is_tasting_kit` independently
   (it is trained to recognise sampler/tasting-pack products), so a kit is
   flagged even when its URL carries no kit token.
2. **Flag** — the bean is stored with `is_tasting_kit = true` and, for
   brand-new products, `requires_review = true`.
3. **Review** — because `requires_review = true`, the bean is **hidden from
   public search** (`/v1/search` and the list endpoints). It appears only in
   the admin UI's *Flagged for review* section.
4. **Approve/Reject** — an admin approves (it really is a real coffee, or the
   kit is acceptable) or rejects the product in the frontend.
5. **Diffjson** — `kissaten apply-review-decisions` reads the admin decisions
   and writes a `*.review.diffjson` (with `requires_review: false`) next to the
   bean's own JSON in the roaster session folder
   (`data/roasters/<roaster>/<session>/<slug>_<hash8>.review.diffjson`).
6. **Refresh** — `kissaten refresh` ingests that diffjson, flipping
   `requires_review` to `false` in the rw DuckDB.
7. **Promote** — `cp data/rw_kissaten.duckdb data/kissaten.duckdb` publishes
   it; the bean is now visible in public search.

## The two flags

| Flag              | Type  | Default | Meaning |
|-------------------|-------|---------|---------|
| `is_tasting_kit`  | bool  | `false` | **Persistent category flag.** The product is a curated multi-coffee tasting kit/sampler/set. Once set, it sticks across stock-update diffs. |
| `requires_review` | bool  | `false` | **Gate flag.** The product is hidden from public search pending human review. Approved products flip it to `false`; rejected products keep it `true` (stays hidden). |

They interact like this:

- `is_tasting_kit` is **persistent**: `_apply_product_flags` keeps a value the
  AI already set even when the URL has no kit token, and re-flagging a known
  kit during stock updates preserves it.
- `requires_review` is only set for **brand-new** products
  (`is_new=True`). Stock-update diffs pass through the same helper with
  `is_new=False` and never re-hide a previously-approved kit.
- `is_tasting_kit` is always a **hard filter** in search (like `is_decaf`);
  `requires_review` is a hidden-row gate.

## URL classification

`BaseScraper._get_tasting_kit_url_patterns()` returns the tokens that mark a
product URL as a kit:

```
["taster-pack", "taster_pack", "sample-pack", "sampler", "tasting-kit", "tasting-set"]
```

Roasters override this to add their own kit tokens. Equipment/services
(`grinder`, `v60`, `subscription`, `gift-card`, …) are still excluded from
`is_coffee_product_url()` — only kit/sampler products are pulled in and
flagged. Seasonal non-kit items that should stay excluded are handled with a
roaster-level override of `_get_excluded_url_patterns()` (e.g. Skylark's
`12-days-of-christmas`).

## How admins review

In the frontend, the admin page lists every bean with `requires_review = true`
under *Flagged for review*. Each row lets the admin **approve** or **reject**.
The frontend stores the decision as a `page_feedback` row with
`kind = 'product-review'` and `fields[0] = {"key": "decision", "value":
"approved" | "rejected"}`.

## How `apply-review-decisions` works

```
kissaten apply-review-decisions --from-db <path> [--data-dir ...] [--dry-run]
```

- Reads `page_feedback` rows with `kind = 'product-review' AND status = 'new'`
  from the frontend SQLite DB (`--from-db`, typically `local.db`).
- Takes the **latest** decision per `entity_url_path` (rowid ascending; last
  wins).
- **Approved** products: looks up the backing bean JSON under
  `--data-dir/roasters` and writes a diffjson next to that bean's JSON, i.e.
  `data/roasters/<roaster>/<session>/<slug>_<hash8>.review.diffjson` containing
  `{"url": ..., "requires_review": false}`. Rows whose `entity_url_path` has no
  matching bean JSON are **skipped** (and left `new`) so a later run can retry.
  Entity paths are matched in **both** the timestamped (raw `bean_url_path`,
  as stored by refreshes that predate timestamp-stripping) and the
  timestamp-stripped form, for forward/backward compatibility.
- **Rejected** products: write **no** diffjson (they stay hidden) and are
  marked applied.
- Marks each processed row `status = 'applied'`. Idempotent: re-running only
  processes rows still in `'new'`.
- `--dry-run` previews every decision and writes/marks nothing.
- `--update-db` (non-dry-run only) additionally writes `requires_review = false`
  for each approved bean directly into the rw DuckDB (`data/rw_kissaten.duckdb`,
  or `KISSATEN_DATABASE_PATH` if set), so the approval takes effect before the
  next `kissaten refresh`. It is best-effort: if the rw DB cannot be opened, the
  diffjson files are still written and apply on the next refresh. Either way,
  promotion still needs `cp data/rw_kissaten.duckdb data/kissaten.duckdb` + a
  serve restart for the API to serve the change.

### Diffjson glob note

`kissaten refresh` picks up partial updates with the recursive glob
`data/**/*.diffjson` (see `src/kissaten/api/db.py`). Because it is recursive,
the review diffjson written next to the bean's JSON under
`data/roasters/…/` is picked up exactly like scraper-produced diffjson — no
extra wiring is needed to get an approved review into the rw database.

### Single-host note for `--from-db`

The command reads the frontend database **read-only** and writes decisions
back to it. It is designed to run on the **same host as the frontend** (or
against a copy) — the frontend uses libsql (WAL mode); the command opens the
main file read-only and falls back to `immutable=1` if a WAL/lock error
occurs. Run it where the SQLite file is reachable, then `kissaten refresh` on
the host that owns the data directory.

## Known tradeoff

The first scrape after this pipeline was rolled out re-extracts kits that were
previously **excluded** (~54 roasters had a `sample`/`taster-pack` substring
exclusion). That produces an initial review queue of every newly-flagged kit.
Also, by design, any legitimate product name or URL containing a kit token
(e.g. a coffee called "sample" or a "taster" menu) lands in the review queue
until an admin approves it. This is intentional: better to surface a doubtful
product to a human than to silently drop it or let it leak into public search.