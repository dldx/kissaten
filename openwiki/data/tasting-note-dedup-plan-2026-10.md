---
type: "Plan"
title: "Tasting Note Canonicalisation (Plural / Spelling Dedup) — 2026-10"
description: "Plan to collapse duplicate tasting notes that are the same word in plural or near-identical spelling (Raisin/Raisins, Date/Dates, Wine Gum/Winegum/Wine Gums) by adding a canonical-note layer built on the existing raw-note -> tertiary_category mapping, plus a deterministic dedup pass over tasting_notes_categorized.csv. No bean JSON rewriting required."
---

# Tasting Note Canonicalisation — 2026-10

## Problem

`/tasting` (and `/flavours`, and the sunburst, and `/v1/stats`) show near-duplicate
chips for the same flavour: **Raisin** (238 beans) next to **Raisins** (86),
**Date** (36) next to **Dates** (112), **Wine Gum** / **Winegum** / **Wine Gums**
all present, **Blackcurrant** / **Black Currant** / **Black Currants**,
**Stone Fruit** / **Stone-Fruit** / **Stonefruit** / **Stone Fruits** /
**Stonefruits** / **Stone Fruit Sweetness** / **Stonefruit Sweetness** /
**Stone Fruit Acidity** / **Stonefruit Acidity**.

Worst offenders by combined bean count (measured on `data/kissaten.duckdb`,
latest row per `clean_url_slug`):

| canonical | variants | combined beans |
|---|---|---|
| Caramel | Caramel, Caramels | 1205 |
| Orange | Orange, Oranges | 845 |
| Floral | Floral, Florals | 880 |
| Apricot | Apricot, Apricots | 775 |
| Sweet | Sweet, Sweets | 269 |
| Plum | Plum, Plums | 743 |
| Mango | Mango, Mangos | 563 |
| Clementine | Clementine, Clementines | 110 |
| Tropical Fruit | Tropical Fruit, Tropical Fruits | 359 |
| Raisin | Raisin, Raisins | 324 |
| Wine Gum | Wine Gum, Winegum, Wine Gums, Winegums | 38 |

## Root cause

There is **no normalisation of tasting notes anywhere in the pipeline**. The only
transformations applied are `.strip().title()` in the Pydantic validator and
exact-string dedup within a single bean. Note names are free-text surface forms
produced independently by ~400 roaster scrapers, and `tasting_notes_categories`
keys on the raw string, so each spelling is an independent primary key with an
independent bean count.

The chain, with the point at which each variant becomes irrecoverable:

1. **Scrape time** — `src/kissaten/scrapers/base.py` contains **zero** references
   to `tasting_note`. Each scraper extracts notes itself, e.g.
   `scrapers/nir_coffee.py:333-335` and `scrapers/naughty_dog.py:367-377`:
   `split()` on delimiters → `.strip().title()` → exact-string `seen` set. Whether
   a roaster writes "raisins" or "raisin" passes straight through.
2. **Schema validator** — `src/kissaten/schemas/coffee_bean.py:436-458`
   (`clean_tasting_notes`, inherited by `CoffeeBeanOptional` at `:564` and by
   `CoffeeBeanDiffUpdate` at `:136-155`) does `.strip().title()` and intra-bean
   exact-string dedup. `split_tasting_notes_if_needed` (`:15-50`) only splits, never merges.
3. **JSON → DuckDB** — `api/db.py:2244` `COALESCE(tasting_notes, [])` inserted
   **verbatim**; diffjson path `api/db.py:1400-1404` likewise.
4. **Mapping table** — `api/db.py:1104-1113`:
   ```sql
   CREATE TABLE IF NOT EXISTS tasting_notes_categories (
       tasting_note VARCHAR PRIMARY KEY,   -- PK on the RAW string
       primary_category VARCHAR, secondary_category VARCHAR,
       tertiary_category VARCHAR, confidence DOUBLE
   )
   ```
   No canonical/normalized column. Contrast `origins`, which has
   `region_normalized`, `farm_normalized`, `state_canonical`, `process_slug`
   plus four registered normalizer UDFs (`api/db.py:417-421`).
5. **CSV growth** — `ai/tasting_note_categorizer.py:354` computes
   `all_db_notes - set(existing_categorizations.keys())` — a plain set difference
   over raw strings — and appends **one new row per new string**
   (`:500-509`). No merge/alias step. This is precisely how `"Raisins"` came to sit
   beside `"Raisin"`. `remove_stale_notes` (`:381-391`, used by
   `categorize tasting-notes --cleanup`) only deletes; it never merges.
6. **Reload** — `load_tasting_notes_categories` (`api/db.py:2617-2636`) is
   `DELETE FROM tasting_notes_categories` + `INSERT INTO … SELECT * FROM read_csv_auto(...)`.
   Blind reload, no `INSERT OR REPLACE`, no merge step. (Good news: a deduped CSV
   propagates cleanly on the next refresh.)
7. **API** — `/v1/tasting-note-categories` (`api/main.py:6594-6629`) joins exactly:
   ```sql
   LEFT JOIN filtered_beans fb ON tnc.tasting_note = fb.note   -- case-sensitive, no stemming
   ```
   then groups only along the category axis, so every spelling is its own row with
   its own `bean_count`. `total_unique_descriptors` (`api/main.py:6651`) is a
   `set()` of raw strings, so `Raisin`+`Raisins` counts as 2.
8. **Frontend** — the only aggregation is `mergeDynamicFlavours`
   (`frontend/src/lib/tasting/conversation.ts:78-85`), keyed on the raw string:
   ```ts
   notesMap.set(nc.note, (notesMap.get(nc.note) || 0) + nc.bean_count);
   ```
   → `Raisin`(238) and `Raisins`(86) render as two chips instead of one `Raisin`(324).
   Note `conversation.ts:87` only re-merges the curated singular seed list
   (`:152-156`, `["Date","Fig","Prune","Raisin"]`) when the API returns **fewer
   than 3** notes — Dried Fruit returns dozens, so the seed is discarded entirely.
   `frontend/src/lib/utils/sunburstDataTransform.ts:86-143` creates one sunburst
   leaf per exact string (`findOrCreateLeaf`), and
   `frontend/src/lib/tasting/reconstruct.ts:43-58` matches skeleton flavours by
   case-sensitive exact equality.

**No existing tool covers this.** `deduplicate-mappings` is case-only (`lower()`
grouping, `ai/varietal_categorizer.py:564-595`) and scoped to two JSON files —
varietal + processing (`cli/main.py:2985-2988`); `deduplicate-regions` is geocoding;
`src/kissaten/dedup/` is farms/producers only. `grep -i "singular|plural|lemmat|stemming"`
over `src/`, `frontend/src/`, `scripts/`, `docs/`, `openwiki/` returns only the
categorizer prompt string (`ai/tasting_note_categorizer.py:135-141`) and unrelated hits.

## Scale of the problem (measured)

Against `src/kissaten/database/tasting_notes_categorized.csv` (5,377 rows):

| class | groups | rows |
|---|---|---|
| Plural pairs (`ies→y`, `(s|x|z|ch|sh)es→∅`, `s→∅` per token) | **301** | 602 |
| …of which byte-identical `primary/secondary/tertiary` | 275 | 550 |
| …of which conflicting categories | **26** | 52 |
| Non-plural spelling groups (casefold + strip `[\s\-'/’.]` + strip `.`) | **110** | ~240 |
| Fuzzy near-dupe pairs (difflib ratio ≥ 0.92, non-plural) | 169 | — |

Coverage: 7,007 distinct notes are attached to live beans; only 5,177 resolve in the
CSV, so **1,830 notes have no category row at all**. Because the join at
`api/main.py:6611` is driven *from* the mapping table, those 1,830 notes are
**invisible on `/flavours` and `/tasting-note-categories` entirely**, and come back
with `primary_category = NULL` from the correlated-subquery sites
(`api/main.py:2391, 2718, 3095, 4449, 4842, 5820, 6355`).

The 110 spelling groups are mostly mechanical — hyphenation, spacing, curly vs
straight apostrophes, trailing periods, and closed compounds:

- hyphen/spacing: `Black-Raspberry`/`Black Raspberry`, `Full-Bodied`/`Full Bodied`,
  `Stone-Fruit`/`Stone Fruit`, `Lemon-Lime Soda`/`Lemon Lime Soda`/`Lemon/Lime Soda`,
  `Passion-Fruit`/`Passion Fruit`/`Passionfruit`
- closed compounds: `Grape Fruit`/`Grapefruit`, `Water Melon`/`Watermelon`,
  `Lemon Peel`/`Lemonpeel`, `Musk Melon`/`Muskmelon`, `Sweet Lime`/`Sweetlime`,
  `Earl Grey`/`Earlgrey`, `Rose Water`/`Rosewater`, `Root Beer`/`Rootbeer`,
  `Ginger Bread`/`Gingerbread`, `Brown Sugar`/`Brownsugar`, `Honey Suckle`/`Honeysuckle`,
  `Passion Fruit`/`Passionfruit`, `Malt Loaf`/`Maltloaf`, `Bubble Gum`/`Bubblegum`,
  `Dragon Fruit`/`Dragonfruit`, `Candy Floss`/`Candyfloss`, `Cacao Nibs`/`Cacaonibs`,
  `Rhubarblike Acidity`/`Rhubarb-Like Acidity`, `Finger Lime`/`Fingerlime`
- apostrophe variants: `Baker's Chocolate`/`Baker'S Chocolate`/`Bakers Chocolate`,
  `S'Mores`/`S’Mores`, `Buddha's Hand`/`Buddha’S Hand`, `True Love's Kiss`/`True Love’S Kiss`,
  `Pu-Erh Tea`/`Pu'Erh Tea`
- stray punctuation from splitting on commas: `Ripe, Tropical Fruits`, `Soft, Honeyed Sweetness`,
  `Soft, White Florals`, `Sugar Cane.`, `White Flower.`

Closed compounds are the one class worth flagging: `Grape Fruit`→`Grapefruit` is safe,
but `Lemon Lime`/`Lemon-Lime` must **not** collapse to `Lemonlime`, and
`Black Currant`→`Blackcurrant` must not collapse to `Blackcurrants`-as-a-distinct-flavour
or lose the `Redcurrant` tertiary that `White Currant`→`Whitecurrant` maps to. Any
compound-joining rule must therefore be **derived from an explicit alias list**, not
inferred.

## Key decision: canonical form = the existing mapping, no bean JSON rewrite

`tasting_notes_categories` already contains the raw→canonical mapping we need:
`tertiary_category` is populated with the **singular canonical** label
(`Raisins`→`Raisin`, `Dates`→`Date`, `Black Currants`→`Blackcurrant`,
`Tropical Flavors`→`Tropical Fruit`). This is LLM-produced but curated, and every
`flavors` list in `src/kissaten/database/taste_lexicon.json` is singular-only
(`Date`, `Raisin`, `Plum`, `Grape`) — confirming singular was the intent all along.

So the fix **does not require rewriting `data/roasters/**/*.json`**. Every raw
variant stays exactly as the roaster published it; canonicalisation happens at
**read time**, in the API join and the frontend aggregation. This is the same shape
as the existing region/farm/process normalisation (`region_normalized` →
`get_canonical_state`), just applied to a `VARCHAR[]` element-wise instead of to a
scalar column, and it has three concrete advantages:

- **Non-destructive.** A wrong alias is a one-line CSV/JSON edit, not a
  multi-thousand-file rewrite that has to be re-run on the next scraper version bump.
- **Self-healing for new variants.** The next roaster that writes "Grapefruits"
  gets an alias automatically, with no new scrape.
- **No scraper churn.** ~400 scrapers keep passing strings through untouched;
  `coffee_beans.tasting_notes` stays the faithful record of what the roaster said.

The cost is that the alias table must be applied **consistently** at every place
that groups or filters notes, or the same split reappears. That inventory is
Step 4 below.

## Plan

### Step 1 — Decide the canonical form for the 26 conflicting pairs

The 26 groups whose variants disagree on `primary/secondary/tertiary` cannot be
collapsed mechanically. **These are resolved by hand now** (see the table at the
end of this page — all 26 have a recorded decision and rationale). Two mechanical
rules cover the other 275:

- **Group key:** lowercase, then per token strip a trailing `ies`→`y`
  (len > 4), `(s|x|z|ch|sh)es`→`∅` (len > 3), or `s`→`∅` (len > 3, not `ss`).
- **Canonical pick:** prefer the row with a populated `tertiary_category`
  (it names a real flavour, not a catch-all); then higher `confidence`; then the
  shorter spelling as the final tiebreak.

Representative rows and the reasoning:

| CSV rows | decision |
|---|---|
| `Raisin` / `Raisins` | auto-merge, identical categories |
| `Dates` / `Date` | auto-merge, identical categories |
| `Botanical` → `Green/Vegetative`, `Botanicals` → `Floral` | keep `Botanicals`→Floral (11 beans total) |
| `Bruised Plum` → `Other` conf 0.1, `Bruised Plums` → `Fruity/Other Fruit/Plum` 0.9 | take the `Bruised Plums` categorisation, canonical name `Bruised Plum` |
| `Clementine` → `Fruity/Citrus/Orange` 0.95, `Clementines` → `Other` 0.1 | take `Clementine`'s categorisation (107 vs 3 beans) |
| `Dried Raspberry` → `Fruity/Dried Fruit`, `Dried Raspberries` → `Fruity/Berry/Raspberry` | keep both distinct — Dried Fruit and Berry are different secondary categories |
| `Dried Tropical Fruit` → `Fruity/Tropical Fruit`, `Dried Tropical Fruits` → `Fruity/Dried Fruit` | keep `Dried Tropical Fruit` under `Fruity/Fruity/Tropical Fruit` (canonical) and let `Dried Tropical Fruits` alias to it; `Dried Fruit` secondary is the weaker label |
| `Flower` → `Floral/'null'/'null'` 0.95, `Flowers` → `Floral/''/''` 1.0 | merge to `Flower`, `Floral`, no secondary (14 beans) |
| `Jaffa Cake` → `Cocoa` 0.8, `Jaffa Cakes` → `Fruity/Citrus/Orange` 0.8 | keep both; Jaffa cake is a confection, the citrus reading is a mis-categorisation worth fixing separately |
| `Sweet` → `Sweet` 0.95, `Sweets` → `Taste Basics` 0.95 | merge to `Sweet` (269 beans) |
| `Wine Gum`/`Winegum` → `Alcohol/Fermented`, `Wine Gums`/`Winegums` → `Fruity` 0.6 | merge all four to `Wine Gum` under `Alcohol/Fermented` (38 beans) |
| `Gummy Bear` → `Sweet` 0.75, `Gummy Bears` → `Fruity/Fruity` 0.85 | take `Gummy Bears`' categorisation, canonical name `Gummy Bears` (14 beans) |

### Step 2 — Introduce the canonical layer in the DB layer

Add to `src/kissaten/database/` a checked-in alias asset (mirroring
`farm_mappings.json` / the region mappings already loaded in `api/db.py`), mapping
each raw note to `(canonical_note, primary, secondary, tertiary)`. Two options:

- **(a) Normalise the CSV in place** — collapse each group to one row keyed by the
  canonical note. Smallest change; the CSV stays the single source of truth.
  Downside: the raw spelling disappears, so bean rows carrying `"Raisins"` stop
  joining at `api/main.py:6611` and silently drop to 0 beans — this **breaks the
  existing data** unless the join is also relaxed. Rejected as a standalone option.
- **(b) Add a canonical column, keep raw rows** — new
  `tasting_note_canonical VARCHAR` on `tasting_notes_categories`, populated for the
  ~840 aliased rows and set equal to `tasting_note` otherwise. All consumers join
  and group on the canonical column. This is the recommended option.

With (b) the CSV gains a sixth column, so `load_tasting_notes_categories`
(`api/db.py:2617-2636`) must select columns explicitly rather than
`SELECT * FROM read_csv_auto(...)`, and needs an `ensure_*` migration for the new
column (`api/db.py:516-683` pattern — rw-mode only, no-op on read-only API).

Also register a `normalize_tasting_note(note VARCHAR) -> VARCHAR` UDF next to
`normalize_process_name` / `normalize_varietal_name` (`api/db.py:415-422`,
`podcast_db.py:43-69` mirrors the list), so SQL can canonicalise a `VARCHAR[]`
element-wise:

```sql
list_transform(cb.tasting_notes, x -> normalize_tasting_note(x))
```

This mirrors the existing `list_transform(cb.origin.variety_canonical, x -> normalize_varietal_name(x))`
pattern at `api/db.py:653` / `:2361`.

### Step 3 — Deterministic dedup pass over the CSV

New CLI command `kissaten deduplicate-tasting-notes`, modelled on
`deduplicate_mappings` (`cli/main.py:2963-3047`). The nice property of that command
is its proof-of-safety argument (`ai/varietal_categorizer.py:564-595`): because the
validator groups by `lower()` only, every group is a pure case-variant, so
collapsing is provably safe and genuine conflicts are left intact for human review.
Extend the same shape here — collapse only where the decision is provably safe,
emit a report otherwise.

```
kissaten deduplicate-tasting-notes [--dry-run] [--report <path>] [--apply]
```

1. Load the CSV; group by the plural-singular key.
2. Groups where all variants share byte-identical categories (275) → **auto-collapse**.
3. Groups with conflicting categories (26) → resolve from the Step 1 decision table
   (checked-in, human-authored — the command does not guess).
4. Spelling groups (110) → only collapse where the alias is in the checked-in
   alias list. Never infer compound-joining.
5. `--dry-run` prints the before/after note counts and the affected rows;
   `--apply` rewrites the CSV. Idempotent: re-running is a no-op.
6. Report includes, for each collapsed group, the merged bean count, so the
   maintainer can eyeball that nothing absurd happened (e.g. `Sweet` 267+2=269).

Adjacent cleanup found during this investigation, to fold into the same pass:
**95 CSV rows carry the literal string `"null"`** in a category column (e.g.
`Boquete Rojo` → `['null','null','null']`, `Abeba` → tertiary `Null`). The endpoint
only filters on `primary_category` (`api/main.py:6616`), so a literal `null` in
`secondary_category`/`tertiary_category` renders in the UI. Treat the literal
string `null` as SQL NULL on load.

### Step 4 — Apply the canonical key at every consumer

This is the part that must not be skipped, otherwise the split just moves. Full
inventory, all currently exact-match unless noted:

| Location | Current | Needed |
|---|---|---|
| `api/main.py:6594-6629` `/v1/tasting-note-categories` | `tnc.tasting_note = fb.note`; groups by category only | join + group on canonical; `list(...)` returns canonical names |
| `api/main.py:6651` `total_unique_descriptors` | `set()` of raw strings | `set()` of canonical strings |
| `api/main.py:6837-6880` `/v1/tasting-notes/{note}/details` | `WHERE tasting_note = ?` | resolve input → canonical first; count `beans_using_note` over all variants |
| `api/main.py:3246-3263` `/v1/stats` "common tasting notes" | `GROUP BY note` on the raw array | `list_transform` to canonical, then group |
| `api/main.py:3272-3303` roaster flavour distribution | `tnc.tasting_note = u.note` | canonical join |
| `api/main.py:6709, 6731` `/v1/search/by-tasting-category` | `array_to_string(...) LIKE '%' \|\| tnc.tasting_note \|\| '%'` | exact `list_contains` on the canonical array — **also fixes a substring bug**: today `Date` matches `Dried Date` and `Plum` matches `Plum Pudding` |
| `api/main.py:1046` flavour-family expansion | `lower(tnc.tasting_note) = lower(note)` | canonical |
| `api/main.py:2391, 2718, 3095, 4449, 4842, 5820, 6355` | `(SELECT primary_category … WHERE tasting_note = note_value LIMIT 1)` | canonical; **also fix `LIMIT 1` on a non-unique key**, which makes the category non-deterministic across variants |
| `api/db.py:2639-2669` `coffee_beans_with_categorized_notes` view | `INNER JOIN … note_table.note = tnc.tasting_note` | canonical |
| `api/main.py:1836-1850` roaster `UniquenessReport` flavour dimension | exact join | canonical |
| `analysis/coffee_comparison.py:423` | `t.note = tnc.tasting_note` | canonical |
| `conversation.ts:78-85` / `:99-124` `mergeDynamicFlavours` | `notesMap` keyed on raw string | key on canonical |
| `conversation.ts:87` seed re-merge guard | only merges seed when API returns `< 3` notes | always merge seed flavours missing from the canonical set |
| `sunburstDataTransform.ts:86-143` | `findOrCreateLeaf(note.note)` per exact string | one leaf per canonical |
| `tastingNotesStore.svelte.ts:23-34` `populateNoteCategoryMap` | lowercases, no canonicalisation | canonicalise keys |
| `tasting/reconstruct.ts:43-58, 110` | case-sensitive skeleton equality | canonical compare |
| `TastingNoteCategoryCard.svelte:73-95` | `filteredNotes.includes(item.note)` | compare canonical |

**Also worth doing in the same change:** the `/v1/tasting-note-categories` LEFT JOIN
is driven from `tasting_notes_categories`, so the 1,830 live notes with no CSV row
never appear. Either add an `INNER`-direction `unnest` for unmapped notes (surfaced
under an "Uncategorised" primary) or `categorize tasting-notes --update-missing` to
close the gap. This is a separate concern from dedup but the same query.

### Step 5 — Prevent regression

- **`clean_tasting_notes`** (`schemas/coffee_bean.py:436-458`): collapse
  duplicates that resolve to the same canonical note within one bean, so a single
  bean never carries both `Raisin` and `Raisins`. Cheap, and stops the array from
  being self-inconsistent.
- **`TastingNoteCategorizer.get_notes_to_process`** (`ai/tasting_note_categorizer.py:348-371`):
  subtract on **canonical** keys, so a new variant of an already-known note is not
  appended as a fresh row. This is the root cause of the growth, so closing it here
  matters more than the one-off CSV cleanup.
- **`load_tasting_notes_categories`**: explicit column list + conflict policy so a
  re-run of `categorize tasting-notes` cannot silently reintroduce a plural row.

### Step 6 — Tests

- `tests/unit/test_tasting_note_canonicalization.py`: the plural key function
  (`ies`, `(s|x|z|ch|sh)es`, `s` not `ss`, len guards, mixed case, multi-token),
  the alias-table lookup, and the conflict decision table.
- Dedup command: idempotency (running twice yields the same CSV), `--dry-run`
  makes no writes, auto-collapse only fires on byte-identical categories, and the
  26 conflict groups resolve to their recorded decision.
- API: `/v1/tasting-note-categories` returns one entry for `Raisin` with the summed
  `bean_count`; `/v1/tasting-notes/Raisins/details` resolves to the canonical
  `Raisin` and counts beans across both variants;
  `/v1/search/by-tasting-category` no longer matches `Dried Date` when searching
  `Date`.
- `validate-db` (`docs/`-documented check set) has a volume-drift check against a
  snapshot; a canonicalisation that legitimately changes note counts needs either a
  snapshot refresh in the same PR or a tolerance, otherwise promotion will fail.

## Risks

- **`/v1/search/by-tasting-category` currently over-matches.** Fixing the LIKE join
  to an exact membership test *reduces* result counts. That is a correctness fix, but
  if any snapshot or test asserts the inflated count, it will surface as a failure.
- **Canonical naming changes user-visible labels.** `Stone Fruits` chips become
  `Stone Fruit`. Worth a deliberate pass over the ~30 groups where the canonical
  choice is not obviously the dominant spelling.
- **The literal-`"null"` cleanup** changes rendered categories for 95 notes.
- **`LIMIT 1` subqueries** (`api/main.py:2391` etc.) become non-deterministic once
  several raw rows map to one canonical; must fix in the same change, not after.
- **Sequenced rollout.** Do Step 2 + 3 (canonical column + deduped CSV) and Step 4
  in one PR, or the DB and API disagree and notes vanish.

## Evidence / how to reproduce

```bash
# distinct notes on live beans vs notes with a category row
KISSATEN_ALLOW_PRODUCTION_DB=1 uv run python - <<'PY'
import duckdb
c = duckdb.connect('data/kissaten.duckdb', read_only=True)
print(c.execute("""
  SELECT COUNT(DISTINCT n) AS live_notes,
         COUNT(DISTINCT CASE WHEN tnc.tasting_note IS NOT NULL THEN n END) AS mapped
  FROM (SELECT unnest(tasting_notes) n FROM (
          SELECT tasting_notes, ROW_NUMBER() OVER (
            PARTITION BY clean_url_slug ORDER BY scraped_at DESC) rn
          FROM coffee_beans) WHERE rn = 1) f
  LEFT JOIN tasting_notes_categories tnc ON tnc.tasting_note = f.n
""").fetchall())
PY
```

Group counts (plural / spelling / fuzzy) are reproduced by the script described in
Step 3 against `src/kissaten/database/tasting_notes_categorized.csv`.

## Related

- [Tasting Notes Non-Flavour Audit — 2026-08](tasting-notes-non-flavour-audit-2026-08.md)
  — the precedent for manual CSV curation on this table. Every edit there was a
  whole-row deletion; this plan is the merge/alias counterpart, and its follow-ups
  (quality/amplitude descriptors such as `Rich`, `Smooth`, `Bold`, `Heavy Body`) are
  still open.
- [Hierarchical Flavour Search — 2026-09](../operations/hierarchical-flavour-search-2026-09.md)
  — the flavour-family expansion whose exact join (`api/main.py:1046`) is in scope.
- [Name Mappings](name-mappings.md) — describes `tasting_notes_categorized.csv` and
  `taste_lexicon.json`. Note its "~2,700 rows" figure is stale (now 5,377) and its
  framing of `tasting_note` as a raw key never mentions the plural collisions.
  `data-model.md:50` calls `coffee_beans.tasting_notes` an "array of normalized
  strings", which is **inaccurate** — only `.strip().title()` is applied.