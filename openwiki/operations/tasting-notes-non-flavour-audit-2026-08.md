---
type: "Operations"
title: "Tasting Notes Non-Flavour Audit — 2026-08"
description: "Audit of tasting_notes_categorized.csv and bean JSON tasting-notes arrays: identified 76 non-flavour metadata tokens (numbers, times, places, varieties, species, processes, field labels) mis-tagged as flavour notes, plus the 50 affected bean files."
---

# Tasting Notes Non-Flavour Audit — 2026-08

## Context

`src/kissaten/database/tasting_notes_categorized.csv` is the mapping table (`tasting_note -> primary/secondary/tertiary_category + confidence`) that the AI categorisation pipeline uses to classify each bean's `tasting_notes`. Because it drives categorisation, any **non-flavour metadata** in this table can leak into the beans' categorised notes — and worse, into flavour search results when the confidence is high.

We reviewed the recently changed lines of the CSV (a purely additive change, +627 rows) plus all bean JSON files under `data/roasters/`, and flagged notes that are **not real flavour notes**: numbers, measurements, times, places/farms/washing stations, varieties/species, processes/decaf/brew methods, and literal column/field labels.

## Flagged tokens (76)

The audit produced a flag list of **76 non-flavour tokens** (saved at `/tmp/kissaten_non_flavour_flagged.csv` during the session). Grouped by reason:

| Reason | Examples |
|---|---|
| Numbers / measurements / times | `1:16-17`, `1:2.5-3`, `2150-2200M`, `3 Weeks`, `92°C`, `74112, 74110`, `74158`, `Eth47` |
| Places / farms / stations / origins | `Hambela`, `Gotiti Station`, `Janson`, `Kamwangi Aa`, `Boquete`, `Gedeb, Guji, Ethiopia`, `Panama`, `Santiage Atitlán` |
| Varieties / species / grades | `Arabica`, `Robusta`, `Heirloom`, `Geisha`, `Gesha`, `Bourbon`, `Sl9`, `Marshell`, `Sl28, Sl34`, `Yellow Caturro` |
| Processes / decaf / brew methods | `Washed`, `Natural`, `Classic Washed`, `Red Honey`, `Yellow Honey`, `Non-Decaf`, `Swiss Water® Process Decaffeination`, `Filter`, `Espresso` |
| Roast level | `Roast`, `Light Roast` |
| Field labels | `Altitude`, `Origin`, `Process`, `Variety`, `Farm Name`, `Other Fruit` |

### Notable mis-categorisations in the CSV

A check against `tasting_notes_categorized.csv` found several metadata terms **assigned to flavour categories with high confidence** (which is exactly what makes them show up in flavour search):

| Token | CSV currently says | Why wrong |
|---|---|---|
| `Bourbon` | Alcohol/Fermented, conf **0.9** | Variety, not a flavour |
| `Roast` | Roasted, conf **0.95** | Not a flavour |
| `Marshell` | Sweet, conf **0.7** | Rare coffee varietal |
| `Geisha` | Floral, conf 0.3 | Variety |
| `Gesha` | Fruity, conf 0.1 | Variety |
| `Sl9` | Taste Basics, conf 0.01 | Variety (SL9) |
| `Panama` | Amplitude, conf 0.1 | Origin |

## Database findings

Querying `data/rw_kissaten.duckdb` (read-only, duckdb 1.5.5) against the `coffee_beans.tasting_notes` array:

- **22 bean records** carry flagged notes with the original 66-token list.
- Of those, **20 source JSON files exist** under `data/roasters/`; 2 are DB records whose source files are absent from disk (Roasticious `20260724` scrape — local sessions are 20260808–10). Those 8 tokens (`Gondo Peaberry`, `Kamwangi Aa`, `Kanjathi Peaberry`, `Kigwandi Peaberry`, `Kii Aa`, `Kiringa Aa`, `Ruthagati Aa`, `Turbo`) occur **only** in those missing files.
- The DB `filename` column stores stale absolute paths (`/home/ubuntu/kissaten/data/roasters/...`); the suffix maps onto local `data/roasters/`.

## Application status

**Applied 2026-08-10, two JSON strip passes:**
1. **76-token pass:** all **50** bean JSON files (108 note-occurrences removed; 16 files now empty). Backup at `/tmp/tasting_notes_backup_20260810-230927/`.
2. **56-token sweep-2 pass** (the follow-up CSV sweep tokens): **53** bean JSON files, **74** note-occurrences removed (2 more files now empty). Backup at `/tmp/tasting_notes_backup2_20260810-233415/`.

Both passes verified: only the `tasting_notes` array changed (all other fields byte-identical) and no flagged/sweep token remains.

**CSV cleaned the same day, two passes:**
1. all **76** flagged rows were removed from `tasting_notes_categorized.csv` (5505 → 5429), so the categoriser will not re-import them. Pre-edit backup at `/tmp/tasting_notes_categorized_backup_20260810-231244.csv`. (One token, `Shanon Fruit`, was later restored at the user's request.)
2. a follow-up sweep removed a further **56** whole-note metadata rows the initial flag list never covered (pure processes/times, varieties/lot codes, ratings, field labels, altitude numbers, plus stray coffee-word notes and a dumped description paragraph) — 5430 → 5374. Removal list at `/tmp/csv_sweep2_removed_56.csv`; backup at `/tmp/tasting_notes_categorized_backup2_20260810-233134.csv`.

Known leavers kept by design: "fermented X" flavour descriptors (`Fermented Banana`, ...), festive flavours (`Christmas Pud`), branded flavour references (`French 75`, `Coca Cola Light`), and coffee-blossom/cherry notes.

## Non-coffee products & tasting boxes in saved beans (2026-08-11)

Audit of saved beans under `durand@dldx.org` found **14 saved items that are not roasted coffee beans**: tasting boxes/sets/kits (Blue Bottle Blend Selection x2, Coffee Lab BREWLAB set x2, Apollon's Gold "9 Stars" Box, Roasticious Kenya Top Lot Kit), non-coffee products (T-90 filter papers, mesh bag, APAX mineral concentrates, HIFLUX filters, sipping chocolate powder, barista course, Green Coffee, RDX concentrate).

- **Scraper exclusions**: all 14 product slugs are now blocked from re-scraping — 12 were already covered by existing exclusions (`apollons_gold` 9-stars, `roasticious` kit/green-coffee, `d_stands_for` t90/mesh-bag, `hatch` apax-lab, `onyx_coffee` sipping-chocolate, `poma_coffee` hiflux, `three_marks_coffee` curso-completo-barista, `vuivui` rdx); **2 were added**: `blue_bottle_coffee.py` `exclude_slugs = ["s242", "s006"]` and `coffeelab.py` `_get_excluded_url_patterns()` + `"zestaw-brewlab"`.
- **JSON files removed**: only the two Coffee Lab BREWLAB set files existed locally — `coffee_lab/20260801/brewlab_set_060130.json` + `brewlab_set_washed_060119.json` (moved to `/tmp/tasting_boxes_removed_20260811-000527/`).
- **The other 12 products had no JSON on disk to remove** — confirmed by mapping the relative `kissaten/data/roasters/...` suffix of **all 16 matching `coffee_beans` rows** (there are duplicate/stale rows, e.g. the BREWLAB set exists for both the `20260724` and `20260801` sessions) against local files, and by a filesystem-wide search. Their DB filenames point at an old `/home/ubuntu/...` environment that no longer exists here (see the filename absolute-path gotcha in `data/data-model.md`). All 16 DB rows remain until a `kissaten refresh --incremental` drops them.


## Dry run (JSON strip plan)

With the expanded 76-token list, the dry-run sweep over **every** JSON under `data/roasters/` (11174 readable files) originally found:

- **50 bean files** containing flagged notes, **108 note-occurrences** to remove.
- **16 files drop to 0** tasting notes (their arrays were pure metadata, e.g. the Greytone "brew guide" file).
- Worst offenders: Greytone `gotiti_ethiopia_washed_heirloom` (21 removed), Apollon's Gold `9th_anniversary_all_varieties_flight` (18 removed, entirely metadata), D Stands For decaf kit, Aery/Datura Panama geshas.
- Files per roaster: Archers 18, Datura 5, Aery 3, plus 16 more roasters at 1–2 files.

The plan is recorded at `/tmp/dryrun_plan.json`; target files at `/tmp/files_to_modify.txt` (`_rel.txt` for relative paths). **Since applied — see Application status above.**

## Edit scope

When applied, each affected file is processed as: read JSON → rebuild only the `tasting_notes` array (drop any entry that case-insensitively matches a flagged token) → write back with `json.dump(indent=2, ensure_ascii=False)`, preserving key order and omitting a trailing newline. Verified that `origins`, `description` and every other field round-trip byte-identically — only `tasting_notes` changes.

## Follow-ups

- **Fix the CSV too** — otherwise the next categorisation run will re-import these tokens (especially `Bourbon`, `Roast`, `Marshell`) and re-tag them as flavours. Set them to `None`/non-flavour or correct the category, and sweep the whole CSV for other variety/process/place tokens currently tagged Floral/Fruity/Sweet/Alcohol at high confidence.
- Decide whether **quality/amplitude descriptors** (e.g. `Rich`, `Smooth`, `Bold`, `Heavy Body`, `Clean Finish`) should be treated as non-flavour. They are not flavour notes but are frequently kept as mouthfeel/amplitude descriptors.
- Re-run the strip across both JSON sources and, if desired, the DuckDB `coffee_beans.tasting_notes`/`coffee_beans_with_categorized_notes` after a refresh.
- Check Archers scraper as many are returning no flavour notes
