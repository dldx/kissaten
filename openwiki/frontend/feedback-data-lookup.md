---
type: "Reference"
title: "Feedback Data Lookup"
description: "How to resolve page_feedback rows from the frontend SQLite database (frontend/local.db) to their source coffee bean JSON files by cross-database join against rw_kissaten.duckdb via DuckDB's sqlite extension."
---

# Feedback Data Lookup

## Overview

Page feedback submitted through the site's feedback dialog lands in a **SQLite** table (`page_feedback`) inside `frontend/local.db`, while the coffee bean records live in **DuckDB** (`data/rw_kissaten.duckdb`). To answer "which bean `.json` file should I change for this feedback row?", you can join the two stores directly: DuckDB ships an `sqlite` extension that reads SQLite tables in place, and `coffee_beans` already stores the absolute path of the source JSON in its `filename` column.

## Why a cross-database join works

- `page_feedback.entity_url_path` holds the bean page path, e.g. `/mad_heads_coffee/el_jardin_aerobic_vol_ano_natural_120_hrs_180316`.
- `coffee_beans.bean_url_path` holds the same path (plus a matching `clean_url_slug`), and `coffee_beans.filename` holds the absolute path of the scraped source file, e.g. `…/kissaten/data/roasters/mad_heads_coffee/20260721/el_jardin_aerobic_vol_ano_natural_120_hrs_180316.json`.
- The two databases have **no shared primary key**; the join key is `entity_url_path = bean_url_path`.

## The join query

Run this from the repository root (read-only against both databases):

```sql
LOAD sqlite;

WITH feedback AS (
  SELECT id AS fbk_id, kind, status, entity_url_path
  FROM sqlite_scan('frontend/local.db', 'page_feedback')
)
SELECT fb.fbk_id, fb.kind, fb.status,
       cb.roaster, cb.name, cb.filename, cb.scraped_at
FROM feedback fb
JOIN coffee_beans cb ON cb.bean_url_path = fb.entity_url_path
ORDER BY fb.fbk_id;
```

Open the DuckDB file with a read-only connection (this respects the test/production DB safety guard in `src/kissaten/api/db.py`):

```bash
uv run python3 -c "
import duckdb
con = duckdb.connect('data/rw_kissaten.duckdb', read_only=True)
con.execute('LOAD sqlite')
... # run the query above
"
```

## Result shape

Every `page_feedback` row whose `entity_url_path` matches a current `coffee_beans` row resolves to its source JSON file. Example result set (all `kind='bean'`, `status='new'`):

| fbk_id | roaster | bean | source json |
|---|---|---|---|
| `fbk_dz1600…` | Apollon's Gold | Kotowa Duncan ETH47 | `data/roasters/apollon's_gold/20260731/kotowa_duncan_eth47_natural_204748.json` |
| `fbk_ebjqA…` | Mad Heads Coffee | El Jardin | `data/roasters/mad_heads_coffee/20260721/el_jardin_aerobic_vol_ano_natural_120_hrs_180316.json` |
| `fbk_KNfVH…` | Lilo Coffee Roasters | LiLo COFFEE KISSA GEISHA BLEND 2026 | `data/roasters/lilo_coffee_roasters/20260711/lilo_coffee_kissa_geisha_blend_2026_natural_080134.json` |

## Caveats

- **Absolute-path skew.** `coffee_beans.filename` stores machine-specific absolute paths (the prefix differs between the scraping host and the local checkout). When locating the file on disk, strip to the `data/roasters/...` suffix and re-join with the current working directory.
- **Snapshot history.** `coffee_beans` can hold multiple rows per bean across scrape timestamps (e.g. El Jardin has both `20260716` and `20260721` rows). `scraped_at` near the feedback `created_at` selects the current snapshot; the target is the newest full `.json` for the slug.
- **Delisted beans.** A bean dropped from the catalogue has no current row, so the join returns nothing. Fall back to a filesystem search (`find data/roasters/<roaster> -name '*<slug>*'`) for the last full snapshot.
- **Test data.** Local feedback rows are frequently test submissions (e.g. suggested values like `hello`). Verify the correction is real before editing the JSON, and re-import into DuckDB afterwards.

## Key source files

| File | Purpose |
|---|---|
| `frontend/src/lib/schema/feedback.ts` | Zod schema for the client-side feedback payload |
| `frontend/src/lib/server/database/schema.ts` | Drizzle schema for the `page_feedback` SQLite table |
| `frontend/src/lib/api/feedback.remote.ts` | Server-side submission endpoint |
| `frontend/local.db` | SQLite database holding `page_feedback` (and other frontend tables) |
| `data/rw_kissaten.duckdb` | Read-write DuckDB with `coffee_beans` (source paths in `filename`) |
