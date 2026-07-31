# Cleanup Procedure — Removing Non-Coffee Items from Vault & Data

This document describes how to remove non-coffee items (equipment, merch, bundles, books, courses, etc.) that have been:
1. Saved into a user's vault (`saved_beans` table in `local.db`)
2. Scraped into the data directory (`data/roasters/<roaster>/...`)

The workflow has three parts:
- **(a)** Read the vault from `local.db` (or a snapshot like `../local_YYYY_MM_DD.db`)
- **(b)** Filter the saved beans to find non-coffee items
- **(c)** Quarantine the associated `*.json`, `*.diffjson`, and `*.png` files

> **Always read-only inspect before any destructive step.** The plan-then-execute pattern works well here: enumerate, ask for confirmation, then execute.

---

## 0. Glossary

| Term | Where | Meaning |
|---|---|---|
| `saved_beans` | `frontend/local.db` (SQLite) | User's vault: per-user saved beans. Source of truth for the client. |
| `bean_url_path` | `saved_beans.bean_url_path` | Format `/{roaster_slug}/{bean_slug}_{nanoid}`. Underscores in the slug, nanoid suffix. |
| `clean_url_slug` | `coffee_beans.clean_url_slug` (DuckDB) | Bean slug without the nanoid suffix. |
| `exclude_slugs` | `src/kissaten/scrapers/<roaster>.py` | List of substrings. Matched against the Shopify product handle (hyphenated) or the URL. Used to filter non-coffee products at scrape time. |
| Quarantine | `../quarantine/<YYYY-MM-DD>-cleanup/` | Holding area for files removed from `data/roasters/`. |
| `data/roasters/<roaster_slug>/<timestamp>/` | Filesystem | Per-roaster per-scrape-session data files. |

---

## Part (a): Reading the vault from `local.db`

### 1. Identify the database file

| DB | Location | Notes |
|---|---|---|
| Primary | `frontend/local.db` | The active SQLite used by the SvelteKit backend. |
| Snapshot | `../local_YYYY_MM_DD.db` | Manual snapshots — treat as read-only source for analysis. |

Check that it's a SQLite 3 database and inspect the schema:

```bash
file frontend/local.db              # -> SQLite 3.x database
sqlite3 frontend/local.db ".tables" # should include saved_beans, user, session, ...
sqlite3 frontend/local.db ".schema saved_beans"
```

Expected `saved_beans` schema:

```sql
CREATE TABLE `saved_beans` (
  `id` text PRIMARY KEY NOT NULL,
  `user_id` text NOT NULL,
  `bean_url_path` text NOT NULL,
  `notes` text,
  `created_at` integer DEFAULT (...) NOT NULL,
  `updated_at` integer DEFAULT (...) NOT NULL,
  FOREIGN KEY (`user_id`) REFERENCES `user`(`id`) ON DELETE cascade
);
```

### 2. Find the target user

```bash
sqlite3 frontend/local.db "SELECT id, name, email FROM user;"
```

Note the `user.id` for the email you care about.

### 3. Enumerate their saved beans

```bash
sqlite3 frontend/local.db \
  "SELECT id, bean_url_path FROM saved_beans WHERE user_id = '<user_id>' ORDER BY bean_url_path;"
```

Also useful:

```bash
sqlite3 frontend/local.db "SELECT user_id, COUNT(*) FROM saved_beans GROUP BY user_id;"
```

This tells you how many rows each user owns. **You MUST scope deletions to a specific `user_id`** — otherwise you'd wipe out other users' vaults.

### 4. Cross-reference with `coffee_beans` (DuckDB)

The vault only stores `bean_url_path`. To see the bean name, roaster, description, and URL, query the production DB. **Read-only** — never write to it:

```bash
duckdb data/kissaten.duckdb -c "
SELECT bean_url_path, name, roaster, url
FROM coffee_beans
WHERE bean_url_path IN (
  '/aery_coffee/ufo_dripper_v3_black_150039',
  '/people''s_possession/ppp_temporary_tattoo_130552'
);"
```

If `data/kissaten.duckdb` is locked (a background duckdb process holds it), use the read-write side instead:

```bash
duckdb data/rw_kissaten.duckdb -c "..."
```

When the `coffee_beans` row shows `NULL` for `name`/`roaster`, the bean was previously removed from the production DB — it's an orphan saved row, still safe to delete from `saved_beans`.

---

## Part (b): Filtering for non-coffee items

The vault slugs follow `/{roaster_slug}/{slug_with_underscores}_{nanoid}`. The slug alone often reveals non-coffee items; cross-checking with `coffee_beans.name` and `coffee_beans.description` confirms.

### 1. Patterns that mark non-coffee items

Match against `bean_url_path` (lowercase, underscores). These are substring indicators — confirm each candidate before flagging:

| Category | Slug substrings | Real examples seen |
|---|---|---|
| **Equipment / papers** | `ufo_dripper`, `filter_papers`, `cafetera`, `mesh_bag`, `drip_bags`, `brew_bags`, `booster`, `grinder`, `kettle`, `mill` | `/aery_coffee/ufo_dripper_v3_black_150039`, `/rose_coffee_roasters/sibarist_booster_060119` |
| **Bundles / boxes / kits / sets / collections** | `bundle`, `box`, `kit`, `set`, `collection`, `9_stars`, `blend_selection`, `9th_anniversary` | `/blue_bottle_coffee/blend_selection_3_types_020741`, `/apollon's_gold/the_9_stars_box_9th_anniversary_selection_natural_180034` |
| **Merch / apparel / books / courses** | `tattoo`, `tshirt`, `hoodie`, `mug`, `tumbler`, `shirt`, `book`, `curso`, `course`, `water_for_coffee` | `/people's_possession/ppp_temporary_tattoo_130552`, `/three_marks_coffee/curso_completo_barista_060150`, `/substance_café/water_for_coffee_2nd_edition_unknown_154656` |
| **Cold brew / concentrate** | `cold_brew_concentrate`, `concentrate` | `/assembly_coffee_london/cold_brew_concentrate_natural_141152` |
| **Additives / water / mineral** | `apax_lab_mineral_concentrates`, `mineral_concentrates`, `aquacode`, `sibarist` | `/nostos_coffee/apax_lab_mineral_concentrates_140639`, `/hatch/apax_lab_mineral_concentrates_050318` |
| **Mystery / lucky / sampler** | `lucky_dip`, `mystery`, `sample`, `taster` | `/outpost_coffee_roasters/lucky_dip_180104` |
| **Non-coffee beverages** | `chocolate`, `cascara`, `pods`, `capsules`, `tea` | `/onyx_coffee_lab/sipping_chocolate_powder_natural_090456` |
| **Gifts** | `gift_card`, `gift_set`, `gift_box`, `giftcard` | `/rounton_coffee_roasters/gift_set_coffee_250g_washed_192703` |
| **Green (unroasted) coffee** | `green_coffee` | `/roasticious/green_coffee_washed_170828` — *borderline*: real coffee but unroasted for home roasters; confirm with the user |
| **Coffee-brewing gear** | `rdx`, `mesh_bag`, `mesh-bag`, `brewlab_set` | `/vui_coffee/rdx_090542` (robusta concentrate), `/coffee_lab/brewlab_set_natural_090200` (a brewing set) |

### 2. Disambiguation — what to KEEP

Slugs like `liquid_cheese`, `peachy_oolong`, `mutualism_2_0`, `sweet_soaker`, `winely`, `nestor_lasso`, `wilder_lazo` are **real coffee beans** with creative names. Don't be fooled by the names. **Always cross-check** by pulling `name` and `description` from `coffee_beans`:

```bash
duckdb data/kissaten.duckdb -c "
SELECT bean_url_path, name, roaster, description
FROM coffee_beans
WHERE bean_url_path LIKE '%winely%' OR bean_url_path LIKE '%liquid_cheese%';"
```

A real bean's `description` will mention origin, varietal, processing, altitude, tasting notes. A non-bean's `description` will mention packaging, hardware, shipping, a course curriculum, a tasting bundle, etc.

### 3. Building the confirmation list

Once you've identified candidates, run a single SQL statement against the production DB to print name/roaster/slug for each — this is your sanity-check list to share with the user before any deletion:

```bash
duckdb data/kissaten.duckdb -c "
WITH candidates AS (
  SELECT * FROM (VALUES
    ('<saved_id_1>', '/<roaster>/<slug_1>'),
    ('<saved_id_2>', '/<roaster>/<slug_2>')
    -- ...one row per candidate
  ) AS t(saved_id, bean_url_path)
)
SELECT c.saved_id, c.bean_url_path, b.name, b.roaster
FROM candidates c
LEFT JOIN coffee_beans b ON b.bean_url_path = c.bean_url_path
ORDER BY b.roaster, b.name;"
```

For each row you want to keep, drop it from the candidates list.

---

## Part (c): Deleting from vault + quarantining files

### 1. Delete rows from `saved_beans`

Run inside a transaction. **Scope by `user_id`** so you never touch other users' rows:

```bash
sqlite3 frontend/local.db <<'EOF'
BEGIN TRANSACTION;
DELETE FROM saved_beans
WHERE user_id = '<user_id>'
  AND id IN (
    '<id_1>',
    '<id_2>',
    -- ...
  );
SELECT changes();
COMMIT;
EOF
```

Verify:

```bash
sqlite3 frontend/local.db "SELECT user_id, COUNT(*) FROM saved_beans GROUP BY user_id;"
```

### 2. Add the slug pattern to each roaster's `exclude_slugs`

Each roaster scraper is a Python file in `src/kissaten/scrapers/`. The exclusion list is one of:

- **`self.exclude_slugs = [...]`** on a `ShopifyJsonScraper` subclass — matched against the product **handle** (hyphenated) as substring.
- **Local `excluded_patterns = [...]` or `excluded_products = [...]`** inside `_extract_product_urls_from_store` — matched against the **URL** (lowercased) as substring.
- **Local `excluded_slugs = [...]`** inside a non-Shopify scraper (e.g. `hatch.py`) — matched against the product URL substring.

**Slug format**: hyphens, lowercase. e.g. `"gift-set"`, `"curso-completo-barista"`, `"cold-brew-concentrate"`. Match against the **Shopify handle** (which uses hyphens), not the URL path slug (which uses underscores). Check the actual handle by querying:

```bash
duckdb data/kissaten.duckdb -c "
SELECT name, url FROM coffee_beans WHERE bean_url_path LIKE '%<slug_root>%';"
```

The handle is the trailing portion of the URL after `/products/`. Choose a pattern that is:
- **Specific enough** to match only the non-coffee product (e.g. `"9-stars"` not `"box"` for the Apollon's Gold 9-Stars box)
- **General enough** to catch variants (e.g. `"filters"` for filter papers, not `"hiflux-wave-155-high-fast-filters"`)
- **Not so broad** that it catches real beans (e.g. don't use `"bag"` — would match `bag` in `brew-bag` but also potentially bean names)

For each affected roaster:
1. Locate the file: `ls src/kissaten/scrapers/ | grep -i <roaster>`
2. Find the existing exclusion list (`self.exclude_slugs`, `excluded_patterns`, `excluded_products`, or `excluded_slugs`)
3. Append the new slug pattern
4. If the roaster has NO exclusion list, add one — see `roasticious.py` for how to filter URLs inside `_extract_product_urls_from_store`
5. **Verify imports**: `uv run python -c "from kissaten.scrapers.<module> import <ClassName>; print('OK')"`
6. **Verify lint doesn't regress**: `uv run ruff check src/kissaten/scrapers/<file>.py`. Compare error count to `git stash` + re-check; do not introduce new errors.

### 3. Find and quarantine data files

The data files for a deleted bean live in `data/roasters/<roaster_slug>/<timestamp>/` and use two filename conventions:

| Convention | Pattern | Example |
|---|---|---|
| **AI-extracted** (non-Shopify) | `<slug_underscored>_<nanoid>.json` and `<slug_underscored>_<nanoid>.png` | `ufo_dripper_v3_black_150039.json` |
| **Shopify diffjson** | `<slug-hyphenated>_<hash>.diffjson` and `<slug-hyphenated>_<hash>_out_of_stock.diffjson` | `curso-completo-barista_4fbad7b2.diffjson` |

Use this script (run from the repo root):

```python
#!/usr/bin/env python3
"""Move data files for deleted beans from data/roasters/ to quarantine.

Run from the repository root: uv run python /tmp/quarantine_deleted_beans.py
"""
from datetime import date
from pathlib import Path
import shutil

REPO_ROOT = Path.cwd()  # run from the repo root
DATA_DIR = REPO_ROOT / "data" / "roasters"
QUARANTINE_DIR = REPO_ROOT.parent / "quarantine" / f"{date.today():%Y-%m-%d}-cleanup"

# (roaster_dir_name, slug_root_underscored, slug_root_hyphenated)
DELETED_BEANS = [
    ("aery_coffee", "ufo_dripper_v3_black", "ufo-dripper-v3-black"),
    ("three_marks_coffee", "curso_completo_barista", "curso-completo-barista"),
    # ... one tuple per deleted bean
]

def find_files(roaster_dir, slug_root, slug_root_hyphen):
    """Match any file whose stem starts with slug_root (underscored) or slug_root_hyphen (hyphenated)."""
    if not roaster_dir.exists():
        return []
    matched = []
    slug_u, slug_h = slug_root.lower(), slug_root_hyphen.lower()
    for f in roaster_dir.rglob("*"):
        if not (f.name.endswith(".json") or f.name.endswith(".diffjson") or f.name.endswith(".png")):
            continue
        stem = f.name.lower()
        for ext in (".json", ".diffjson", ".png"):
            if stem.endswith(ext):
                stem = stem[: -len(ext)]
                break
        if stem.endswith("_out_of_stock"):
            stem = stem[: -len("_out_of_stock")]
        if stem.startswith(slug_u) or stem.startswith(slug_h):
            matched.append(f)
    return matched

def move_files(files):
    moved, skipped = 0, 0
    for f in files:
        rel = f.relative_to(DATA_DIR)
        dest = QUARANTINE_DIR / rel
        if dest.exists():
            skipped += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(f), str(dest))
        moved += 1
    return moved, skipped

def main():
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    total_moved = total_skipped = 0
    for roaster, slug_u, slug_h in DELETED_BEANS:
        files = find_files(DATA_DIR / roaster, slug_u, slug_h)
        moved, skipped = move_files(files)
        total_moved += moved
        total_skipped += skipped
        print(f"  [{roaster}/{slug_u}] found={len(files)}, moved={moved}, skipped={skipped}")
    print(f"\nTotal moved: {total_moved}, skipped: {total_skipped}")

if __name__ == "__main__":
    main()
```

#### Caveat: over-matching

Substring matching on the slug root will catch other products that share a prefix. Example: the slug root `cafetera-amor-perfecto` will match both `cafetera-amor-perfecto` (the basic coffee maker) AND `cafetera-amor-perfecto-edicion-especial` (a special-edition variant). The user may or may not want the variant removed. Two strategies:

- **Strict match**: only move files whose stem equals `slug_root_<nanoid>` or `slug_root_<hash>`. Safer but requires knowing the exact nanoid/hash.
- **Loose match + audit**: match by prefix, then list what was moved and ask the user if any over-matched files should be restored.

Rule of thumb: if the over-matched item is also not a coffee bean (e.g. a special-edition coffee maker variant), keep it quarantined; otherwise restore it. **Always ask.**

### 4. Verify

```bash
# No leftover files for any of the deleted slug roots
for slug in "<slug_1>" "<slug_2>" "<slug_3>"; do
  hits=$(find data/roasters -name "${slug}*" -type f \( -name "*.json" -o -name "*.diffjson" -o -name "*.png" \) 2>/dev/null)
  [ -n "$hits" ] && echo "STILL PRESENT: $slug -> $hits"
done
echo "(empty above = all cleared)"

# Total in quarantine
find ../quarantine/$(date +%Y-%m-%d)-cleanup -type f | wc -l
```

### 5. Optional: verify scraper edits

```bash
# Imports still work
uv run python -c "
from kissaten.scrapers.<roaster_1> import <Class1>
from kissaten.scrapers.<roaster_2> import <Class2>
print('All modified scrapers import OK')
"

# Lint does not introduce new errors
uv run ruff check src/kissaten/scrapers/<roaster_1>.py src/kissaten/scrapers/<roaster_2>.py
```

---

## What is **NOT** in scope for this procedure

| Item | Why it's separate |
|---|---|
| `data/kissaten.duckdb` / `data/rw_kissaten.duckdb` rows in `coffee_beans` | The `exclude_slugs` mechanism handles these on the next scrape. `shopify_base.py:277-286` marks matching products out-of-stock via `create_diffjson_stock_updates`, then `validate-db` + promotion propagates. Don't hand-edit DuckDB. |
| `data/kissaten_backup_*.duckdb` snapshots | Read-only backups; not the source of truth. |
| Client-side Dexie `savedBeans` (browser IndexedDB) | The next sync (`pullAndReconcile` in `frontend/src/lib/sync/savedBeanSync.ts`) pulls the deletion from the server `saved_beans` table automatically. |
| `.diffjson` files for products that share the prefix but are unrelated | E.g. `bolsa-navidena-amor-perfecto-edicion-especial` — don't move unless the user explicitly flags it. |

---

## Quick reference — bash one-liners

```bash
# Find the user
sqlite3 frontend/local.db "SELECT id, name, email FROM user;"

# Enumerate their saved beans
sqlite3 frontend/local.db \
  "SELECT id, bean_url_path FROM saved_beans WHERE user_id = '<uid>' ORDER BY bean_url_path;"

# Cross-reference with coffee_beans
duckdb data/kissaten.duckdb -c "
SELECT bean_url_path, name, roaster FROM coffee_beans
WHERE bean_url_path LIKE '%<pattern>%';"

# Count files matching a slug root
find data/roasters -name "<slug_root>*" \( -name "*.json" -o -name "*.diffjson" -o -name "*.png" \) | wc -l

# Verify nothing remains
find data/roasters -name "<slug_root>*" \( -name "*.json" -o -name "*.diffjson" -o -name "*.png" \)

# Count files in quarantine
find ../quarantine/$(date +%Y-%m-%d)-cleanup -type f | wc -l
```
