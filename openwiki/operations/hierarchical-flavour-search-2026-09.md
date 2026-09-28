---
type: "Design"
title: "Hierarchical Flavour Search (Sept 2026)"
description: "Making tasting_notes_query hierarchy-aware so a family term like 'fruity' expands to its child notes, plus the pre-change baseline dataset used to validate it."
---

# Hierarchical Flavour Search (Sept 2026)

## Goal

Make the single existing `tasting_notes_query` parameter hierarchy-aware: a bare
family term such as `fruity` should return the whole **Fruity** family (every
child note under that primary/secondary/tertiary branch), not just beans whose
note string literally contains "fruity". No new API parameters are introduced —
existing callers and the AI search URL builder keep using `tasting_notes_query`.

## Current gap

`parse_boolean_search_query_for_field` (`src/kissaten/api/main.py` ~916) turns a
query into `ILIKE` patterns against the serialized note column and never
consults the `tasting_notes_categories` table. So `fruity` compiles to
`%fruity%` and matches only notes containing that substring; siblings such as
"Citrus", "Berry", "Stone Fruit" are invisible unless named explicitly. The
baseline numbers below make the gap concrete: `family_floral` returns 1518 rows
(because "floral" happens to be a literal note) while `family_fruity` returns
only 194.

## Chosen design

- Add an opt-in internal flag `expand_flavour_categories` on
  `parse_boolean_search_query_for_field`. Only the tasting-notes call sites in
  `build_coffee_bean_filters` pass it; other fields keep literal semantics.
- Each **bare, non-quoted term** is OR-ed with a correlated
  `EXISTS (SELECT 1 FROM unnest(cb.tasting_notes) AS u(note)
  JOIN tasting_notes_categories tnc ON tnc.tasting_note = u.note
  WHERE tnc.primary_category LIKE pattern OR tnc.secondary_category LIKE pattern
  OR tnc.tertiary_category LIKE pattern)` subquery, so the term matches both the
  literal note and anything classified under a matching category.
- **Quoted terms stay literal** (`"Peach"`) as an escape hatch for callers that
  want the exact string and nothing else.
- Boolean/wildcard syntax composes: `fruity&!(bitter|sour)` expands `fruity`
  while `!`/`|`/`&`/parentheses continue to bind as today.
- `tasting_notes_query` remains the only public knob; `tasting_notes_only=true`
  (deprecated) follows the same parser path.

## Baseline dataset

- Path: `tests/fixtures/flavour_search_baseline.json` — **1,733,892 bytes
  (~1.65 MB)**, captured at git commit `232dde0`, **untruncated** (every
  query/mode has `truncated: false`; the largest set, `group_berry_lemon_lime`
  relevance at 5073 items, fits in 51 of the 60 allowed pages).
- Reproduce (capture): `python scripts/capture_flavour_search_baseline.py`
  (defaults: `--api-base http://localhost:8000 --per-page 100 --max-pages 60`;
  requires a running API — it does a `GET /v1/health` guard first).
- Reproduce (validate): `python scripts/validate_flavour_search.py`
  (defaults: `--baseline tests/fixtures/flavour_search_baseline.json --api-base
  http://localhost:8000`).
- Contents:
  - `invariant` — top-level string stating the superset rule: hierarchy-aware
    expansion is a pure OR-expansion, so every post-change id set must contain
    every baseline id.
  - `meta` — capture timestamp, API base, git commit, page caps, purpose.
  - `queries[]` — 20 named queries, each with its `request` params, an
    `"expect": "superset"` invariant, and both the `strict`
    (`sort_by=name&sort_order=asc`, exercises the WHERE/ILIKE branch) and
    `relevance` (`sort_by=relevance&sort_order=desc`, exercises the
    granular-scoring branch) result sets. Each mode is deliberately slim:
    `total_items`, `returned_count`, `truncated`, and `ids` (integer bean ids).
  - `category_reference` — the `/v1/tasting-note-categories` hierarchy,
    `{primary: [{secondary_category, tertiary_category, note_count, bean_count,
    tasting_notes}, ...]}`, used to compute expected family children
    independently of search results.

Capture is read-only and idempotent: re-running it simply re-fetches and
overwrites the artifact.

## Validation strategy

`scripts/validate_flavour_search.py` re-runs every baseline query/mode against
the live API (same mode params and pagination) and asserts the new id set is a
**SUPERSET** of the baseline for each; it prints per-query/mode missing counts
and a pass/fail summary, exiting non-zero on any violation. Before the change
lands it passes trivially (API compared to itself); run it after the parser
change to prove no baseline match was lost.

- **Superset is the default invariant for every query/mode** (`expect:
  "superset"`), because the expansion only ORs in additional category matches.
- **Family / substring queries** (`family_fruity`, `family_citrus`,
  `family_nutty`, `family_floral`, `substring_fruit`) should grow; use
  `category_reference` to compute "all notes under X" and confirm the returned
  beans cover them.
- **Optional exact-equality checks** — `--expect-equal <glob>` (default none)
  additionally requires set equality for matching query names. Equality is only
  safe for terms that cannot collide with any tasting-note category display
  name (e.g. `"Peach"`); the final glob list is to be chosen after
  implementation. Any non-family term that is also a category label will
  legitimately grow under expansion, so it must stay on the superset invariant.

## Relevant source

- `src/kissaten/api/main.py` — `build_coffee_bean_filters` (~424, tasting-notes
  branch ~521) and `parse_boolean_search_query_for_field` (~916); the
  `/v1/tasting-note-categories` endpoint (~6412).
- `src/kissaten/ai/search_agent.py` — `_generate_search_url` (~510) emits
  `tasting_notes_query` from `SearchParameters.tasting_notes_search`; update
  the system prompt if family expansion changes the recommended vocabulary.
- `src/kissaten/database/tasting_notes_categorized.csv` — the source rows
  loaded into `tasting_notes_categories`.
- Baseline script: `scripts/capture_flavour_search_baseline.py`;
  validator: `scripts/validate_flavour_search.py`;
  dataset: `tests/fixtures/flavour_search_baseline.json`.

## Outcome (2026-09-27)

**Status: implemented and validated.** The hierarchy-aware `tasting_notes_query`
expansion is live and the superset invariant holds on all 40 query/modes
(20 queries × strict + relevance).

### old → new `total_items`

| query | baseline | new |
|---|---|---|
| `family_fruity` | 194 | **13081** |
| `substring_fruit` | 2888 | **13150** |
| `family_citrus` | 924 | **5518** |
| `family_nutty` | 106 | **2009** |
| `family_floral` | 1518 | **5531** |
| `tasting_notes_only_fruity` (strict) | 194 | **13081** |
| `exact_fruity` | 139 | **139 (unchanged)** |
| `rare_no_match` | 0 | **0** |

Family terms now return the whole category branch. A side effect of the
substring (`%term%`) matching is that literal terms which merely share a
substring with a category display name also expand — e.g. `caramel` matches
"Caramelized", `choc*` matches "Chocolate", `fruit` matches "Other Fruit" — which
is the intended behaviour. Quoted terms (`"Peach"`, `"Fruity"`) remain the
literal escape hatch and are unchanged.

### Validator

`scripts/validate_flavour_search.py` now:

- defaults to `--per-page 100 --max-pages 300` (enough to enumerate the
  ~13,150-row fruit families out of the box);
- honours the per-query `expect` field in the baseline: three term sets cannot
  collide with any category display name and are pinned to `"expect": "equal"` —
  `exact_peach`, `exact_fruity`, `rare_no_match` (all others are `"superset"`);
- prints a `WARNING` to stderr and treats a record still truncated at the page
  cap as **inconclusive** (neither pass nor fail), exiting non-zero only on real
  superset/equality violations;
- keeps `--expect-equal <glob>` as an override/complement.

### Exact repro

Start an isolated second read-only server on :8001 without disturbing :8000.
The launcher patches the AI-search / media-insights / podcast cache paths to
temp files so the running :8000 server's DuckDB locks are not contested:

```python
# /tmp/opencode/launch_8001.py
import os
os.environ["KISSATEN_MEDIA_CACHE_PATH"] = "/tmp/opencode/media_insights_cache_validate.duckdb"
os.environ["KISSATEN_PODCAST_DATABASE_PATH"] = "/tmp/opencode/podcasts_validate.duckdb"
from kissaten.cache.ai_search_cache import AISearchCache
_orig = AISearchCache.__init__
def _patched(self, cache_db_path=None):
    if cache_db_path is None or cache_db_path == "data/ai_search_cache.duckdb":
        cache_db_path = "/tmp/opencode/ai_search_cache_validate.duckdb"
    _orig(self, cache_db_path)
AISearchCache.__init__ = _patched
import uvicorn
from kissaten.api.main import app
uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")
```

```bash
uv run python /tmp/opencode/launch_8001.py &
until curl -sf http://localhost:8001/v1/health >/dev/null; do sleep 1; done
uv run python scripts/validate_flavour_search.py --api-base http://localhost:8001
```

Out-of-the-box (no extra flags) this prints `PASS: all 40 checked query/mode(s)
satisfy the superset invariant, 6 exact-equality.` with no truncation warnings,
then the :8001 server can be stopped; :8000 is untouched.

### Files touched

`src/kissaten/api/main.py`,
`tests/unit/test_flavour_category_expansion.py`,
`tests/test_search_coffee_beans.py`,
`scripts/validate_flavour_search.py`,
`tests/fixtures/flavour_search_baseline.json`,
the AI prompt files (`src/kissaten/ai/search_agent.py`, `src/kissaten/ai/jev/`),
and the frontend flavour-search files.