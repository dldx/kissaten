---
type: flavour-lexicon-concept
title: Tasting Note Taxonomy & Flavour Lexicon
description: How Kissaten models coffee tasting notes as a normalized string array, categorizes them post-hoc into a three-tier SCA-derived flavour hierarchy, and exposes them through AI modules, API endpoints, and interactive frontend charts.
tags: [tasting-notes, flavour-lexicon, sca-flavour-wheel, ai-categorization, sunburst-chart, flavour-profile]
verified:
  - by: openwiki/0.4.3
    at: 2026-08-29T13:59:13.975Z
sources:
  - id: openwiki-source-b979ff9a16e5954daa4c8f47
    resource: repo://docs/GUIDED_TASTING_PLAN.md
  - id: openwiki-source-f3f4df18c941b708126bc31c
    resource: repo://frontend/src/lib/components/FlavourProfileDonut.svelte
  - id: openwiki-source-f13ac1e1991aaa132ea7b161
    resource: repo://frontend/src/lib/components/SunburstChart.svelte
  - id: openwiki-source-6103261e19483a89888909dc
    resource: repo://frontend/src/lib/tasting/conversation.ts
  - id: openwiki-source-14d82312bef47575e0aec2f4
    resource: repo://frontend/src/lib/utils.ts
  - id: openwiki-source-7ce7f9ae61d7a9d7fb46795f
    resource: repo://frontend/src/lib/utils/sunburstDataTransform.ts
  - id: openwiki-source-2fe4734f222de8019144ab5c
    resource: repo://frontend/src/routes/(main)/flavours/%2Blayout.ts
  - id: openwiki-source-e82cbceb50788e7b9c868909
    resource: repo://frontend/src/routes/(main)/flavours/%2Bpage.svelte
  - id: openwiki-source-998a4c105a5fd8b69f16d14e
    resource: repo://frontend/src/routes/(main)/flavours/%2Bpage.ts
  - id: openwiki-source-3caf6a98926cd5705188c6a2
    resource: repo://frontend/src/routes/(main)/roasters/%5Broaster_name%5D/%2Bpage.svelte
  - id: openwiki-source-25b5fb023246da78db3dcf1a
    resource: repo://src/kissaten/ai/tasting_note_categorizer.py
  - id: openwiki-source-33b22e0e1590b8a11b44c31f
    resource: repo://src/kissaten/ai/tasting_note_splitter.py
  - id: openwiki-source-b6db435ba1198be65f340e6b
    resource: repo://src/kissaten/api/db.py
  - id: openwiki-source-9735fcc3e14d5d9974206d6d
    resource: repo://src/kissaten/api/main.py
  - id: openwiki-source-aa7b0286107825e00b412cf8
    resource: repo://src/kissaten/database/taste_lexicon.json
  - id: openwiki-source-ff88345ee75129d53d705bdf
    resource: repo://src/kissaten/database/tasting_notes_categorized.csv
  - id: openwiki-source-0d95f608f6d7d340f981a2cc
    resource: repo://src/kissaten/schemas/api_models.py
  - id: openwiki-source-a91bd1e17d487f691b479d46
    resource: repo://src/kissaten/schemas/coffee_bean.py
  - id: openwiki-source-2dc6f01310832dc3247ee1da
    resource: repo://src/kissaten/schemas/roaster_models.py
  - id: openwiki-source-d8c1deb6e01f74f329dcf580
    resource: repo://tests/test_tasting_notes_order.py
generated: { by: "openwiki/0.4.3", at: "2026-08-29T13:59:13.975Z" }
---

# Tasting Note Taxonomy & Flavour Lexicon

Coffee tasting notes are the free-text flavour descriptors roasters attach to a bean — "Blackberry", "Dark Chocolate", "Citrus Acidity". Kissaten stores them verbatim as a normalized array of strings on each `CoffeeBean`, then categorizes that vocabulary *post-hoc* with AI into a three-tier hierarchy adapted from the SCA Coffee Taster's Flavour Wheel. This page documents the data shape, the splitter/categorizer AI modules, the lexicon and CSV reference files, the DuckDB categorization table, the API endpoints that serve the hierarchy, and the frontend visualizations (the `SunburstChart` flavour wheel and the `FlavourProfileDonut`).

## Why `tasting_notes` is an array of strings, not structured objects

`tasting_notes` on `CoffeeBean` (and its diff-update sibling `CoffeeBeanDiffUpdate`) is a `list[str]`, described as "Flavour notes in order they appear in the description". The raw notes are scraped from roaster product pages and come in every shape — single words, compound phrases, whole sentences, foreign-language terms. Rather than forcing scrapers to commit to a taxonomy at extraction time, Kissaten keeps the original text and defers categorization to an offline AI pass.

The `clean_tasting_notes` field validator enforces three normalization invariants on the array:

1. **Title-casing** — every note is `.strip().title()`-ed.
2. **Deduplication, order-preserved** — a `seen` set drops duplicates while a list keeps the first-seen order, so the roaster's intended prominence is retained.
3. **Splitting of long descriptive strings** — when a single long note looks like a sentence, `split_tasting_notes_if_needed` invokes the `TastingNoteSplitter` AI module to break it into individual concise notes *before* the dedup/title pass.

This is why the array is plain strings: the categorization (primary/secondary/tertiary) is a derived, separately-maintained artefact, not a property of the bean record itself. The API layer later *decorates* these strings with categories on the way out — see [API decoration](#api-decoration-of-tasting-notes) below.

## The TastingNoteSplitter: splitting roaster prose into notes

Roasters frequently write a single descriptive string rather than a list, e.g. *"Notes of blackberry and dark chocolate with a citrus finish"*. `split_tasting_notes_if_needed` (in `schemas/coffee_bean.py`) detects this case with a heuristic: a single-element array whose lone note is longer than 15 characters *and* contains sentence-like markers (`" with "`, `" and "`, `" notes of "`, `". "`, `", "`). When the `GOOGLE_API_KEY` environment variable is set, it constructs a `TastingNoteSplitter` and runs it (in a dedicated thread to avoid async-loop conflicts).

`TastingNoteSplitter` (in `ai/tasting_note_splitter.py`) is a PydanticAI agent backed by `gemini-3.1-flash-lite` with thinking disabled (`thinking_budget: 0`). Its system prompt instructs it to:

- Extract specific flavour words and short phrases (e.g. "Raspberry", "Caramel Sweetness", "Lime Acidity").
- Strip filler, marketing language, and narrative elements.
- Normalize to Title Case.
- Preserve already-separated notes as distinct items.
- Keep acidity/sweetness context (e.g. "Citrus Acidity", "Honey Sweetness").
- If the input is a single flavour description rather than a list, return it as a single-item list.

Its output is a `TastingNotesSplit` model with a `notes: list[str]` field. On any failure (or when the input is under 10 characters) it falls back to returning `[text.strip().title()]` — splitting never throws or blocks bean ingestion.

## The three-tier hierarchy and the SCA Flavour Wheel

The SCA (Specialty Coffee Association) Coffee Taster's Flavour Wheel organizes coffee flavours from broad inner categories to specific outer ones. Kissaten adapts this into a strict three-tier hierarchy:

- **Primary category** — the broad family: `Fruity`, `Floral`, `Sweet`, `Nutty`, `Cocoa`, `Spices`, `Roasted`, `Earthy`, `Green/Vegetative`, `Alcohol/Fermented`, `Sour/Acid`, `Chemical`, `Stale/Papery`, `Cereal`, `Mouthfeel`, `Amplitude`, `Taste Basics`, etc.
- **Secondary category** — a subdivision, present mainly under `Fruity` (`Berry`, `Citrus Fruit`, `Dried Fruit`, `Other Fruit`, and a general `Fruity`). Most primaries have no secondary.
- **Tertiary category** — the specific flavour: `Blackberry`, `Blueberry`, `Strawberry`, `Lemon`, `Bergamot`, `Dark Chocolate`, etc. A tertiary is only ever assigned when a secondary is also present.

The hierarchy is enforced as a hard invariant by the `TastingNoteCategory` Pydantic model: a `model_validator` raises if `tertiary_category` is set but `secondary_category` is absent. The categorization agent's system prompt reinforces this ("a tertiary category REQUIRES a secondary category, and a secondary category REQUIRES a primary category") and gives graded examples — `"chocolate"` → Cocoa/None/None, `"berry"` → Fruity/Berry/None, `"Strawberry Jam"` → Fruity/Berry/Strawberry.

## The taste lexicon (`taste_lexicon.json`)

`taste_lexicon.json` is the controlled vocabulary the categorizer consults. Its top-level shape is:

```json
{
  "_meta": {
    "comment": "This lexicon has been automatically updated with AI-generated tertiary categories.",
    "last_updated": "<ISO 8601 UTC>",
    "warning": "These additions are not official and should be reviewed."
  },
  "categories": [
    {
      "primary_category": "Fruity",
      "secondary_category": "Berry",
      "tertiary_category": null,
      "flavors": ["Blackberry", "Blueberry", "Raspberry", "Strawberry", ...]
    },
    ...
  ]
}
```

Each category block carries its `primary_category`, an optional `secondary_category`, and a `flavors` array of the specific tertiary terms valid under that branch. The `_meta` block records that the lexicon has been *augmented* by AI-suggested tertiary additions (the canonical SCA set plus AI-discovered terms); the warning flag marks these additions as needing human review. The categorizer loads this file and injects the whole JSON into the LLM system prompt so every categorization is anchored to the known vocabulary.

## The TastingNoteCategorizer

`ai/tasting_note_categorizer.py` is the offline pipeline that turns the database's raw note strings into the categorized CSV. It is run via a Typer CLI (`python -m kissaten.ai.tasting_note_categorizer`) and orchestrates three PydanticAI agents, all backed by `gemini-3.5-flash`:

### 1. Categorization agent

`Agent("gemini-3.5-flash", output_type=TastingNoteBatch)` assigns each note a `primary_category`, optional `secondary_category`, optional `tertiary_category`, and a `confidence` in `[0.0, 1.0]`. Its system prompt embeds the lexicon JSON and instructs it to handle synonyms and translations (`"choc"` → `Chocolate`, Spanish `"Fresa"` → `Strawberry`), pick the most specific category for compound notes, and leave `tertiary_category` null for general terms. `categorize_batch` sends notes in batches; on failure it falls back to assigning every note `primary_category="Other"` with confidence `0.1`.

### 2. Naming agent (lexicon expansion)

`Agent("gemini-3.5-flash", output_type=CanonicalNameBatch)` extracts a single canonical flavour word that is *more specific* than a note's parent secondary category. It is instructed to return `null` for mere synonyms or plurals of the parent (e.g. `"Wild Berries"` → null under `Berry`). `update_lexicon_with_new_tertiary_categories` groups all CSV rows that have a secondary but no tertiary, runs the naming agent over them, counts canonical names, and adds any name appearing `>= min_count` (default 3) times and not already present to the lexicon's `flavors` list — then re-sorts and re-saves `taste_lexicon.json` with an updated `_meta` timestamp. This is how the lexicon grows over time.

### 3. Non-flavour check agent (`NonFlavourCheck`)

Some scraped "notes" are not flavours at all — product names, farm/estate names, marketing phrases, altitude values, process codes. The `NonFlavourCheck` model captures this: `is_flavour: bool` plus a `reason`. The non-flavour agent reviews notes previously bucketed as `Other` and classifies each. `recategorize_other_notes` then:

- Marks non-flavours with `primary_category="None"`, confidence `0.0` (these are the `None`/`null`/`no match` rows later excluded from the public categories API).
- Re-runs genuine flavours through the categorization agent to find them a proper home.

The agent leans towards `is_flavour=True` when in doubt, and on failure defaults every note to `is_flavour=True` so nothing is silently discarded.

### CLI and lifecycle

The Typer CLI (`categorize` command) supports three flags:

- `--update-missing` — re-categorize existing notes that lack a tertiary category (in addition to brand-new notes).
- `--cleanup` — remove notes from the CSV that are no longer present in the database (interactive confirm).
- `--recategorize-other` — run the `Other`-bucket cleanup described above.

Default mode processes only notes in the DB but not yet in the CSV. The run always finishes by calling `update_lexicon_with_new_tertiary_categories` so the lexicon and CSV evolve together. Stale-note detection compares `get_unique_tasting_notes_from_db` (a `DISTINCT unnest(tasting_notes)` over `coffee_beans`) against the CSV's keys.

## The categorized CSV and the DuckDB table

`tasting_notes_categorized.csv` (~2,700 rows) is the materialized output of the categorizer. Each row is `tasting_note, primary_category, secondary_category, tertiary_category, confidence` — a flat lookup from a raw note string to its hierarchy position. It includes foreign-language terms, compound descriptions, and non-flavour entries flagged with `None` categories and confidence `0.0`.

At API startup, `load_tasting_notes_categories` (`api/db.py`) bulk-loads this CSV into the `tasting_notes_categories` DuckDB table:

```sql
CREATE TABLE IF NOT EXISTS tasting_notes_categories (
    tasting_note VARCHAR PRIMARY KEY,
    primary_category VARCHAR,
    secondary_category VARCHAR,
    tertiary_category VARCHAR,
    confidence DOUBLE
)
```

Loading clears the table first (`DELETE FROM tasting_notes_categories`) then `INSERT ... SELECT * FROM read_csv_auto(...)`. It also creates the `coffee_beans_with_categorized_notes` view, which joins each bean to its notes' categories via `unnest(cb.tasting_notes)` and aggregates `primary_categories`, `secondary_categories`, `tertiary_categories`, and `avg_categorization_confidence` per bean. This load is part of the database refresh lifecycle invoked at startup.

## API endpoints

### `GET /v1/tasting-note-categories`

The primary endpoint powering the flavours exploration UI. It accepts the full standard filter set (query, fts_query, tasting_notes_query, roaster, origin, region, process, variety, price/weight/elevation/cupping ranges, decaf, single-origin, currency conversion) so the category counts reflect a filtered bean universe.

The query unnests each filtered bean's `tasting_notes`, joins to `tasting_notes_categories`, excludes non-flavour rows (`LOWER(primary_category) NOT IN ('none', 'null', 'no match')`), and groups by the full `primary → secondary → tertiary` hierarchy. For each group it returns:

- `note_count` and `total_bean_count`
- `tasting_notes` — the raw note strings in that group
- `tasting_notes_with_counts` — `{note, bean_count}` structs ordered by bean count

Results are grouped into a `categories` dict keyed by primary category, plus a `metadata` block (`total_notes`, `total_unique_descriptors`, `total_primary_categories`). The endpoint is cached with `SimpleMemoryCache`.

### `GET /v1/search/by-tasting-category`

Searches for beans whose tasting notes fall in a given category. Required `primary_category`; optional `secondary_category`; `min_confidence` threshold (default `0.5`). It joins `coffee_beans` to `tasting_notes_categories` and returns paginated `APISearchResult` objects ordered by average categorization confidence, with pagination metadata.

### `GET /v1/flavour-images`

Serves the flavour imagery used by the `SunburstChart` on hover. It scans the `data/flavours/paintings/` directory for `.jpg` files, derives the note name from each filename (unicode-normalized, underscores→spaces), and enriches each with attribution (author, licence, licence URL) from `wikidata_flavour_images.json`. The frontend's `flavours/+layout.ts` loads this list once and the `flavourImageService` looks up a matching image for the hovered note.

### API decoration of tasting notes

On read paths such as `/v1/search`, the API does not return the raw `tasting_notes` strings alone. A correlated subselect packs each note with its primary category:

```sql
SELECT list(struct_pack(
    note := note_value,
    primary_category := (SELECT primary_category FROM tasting_notes_categories
                         WHERE tasting_note = note_value LIMIT 1)
))
FROM unnest(sb.tasting_notes) AS u(note_value)
```

The `APICoffeeBean.tasting_notes` field is typed `list[TastingNote | str]` to accept either the decorated `{note, primary_category}` structs or plain strings (for backward compatibility). The order of notes is preserved through this decoration — a behaviour explicitly guarded by `tests/test_tasting_notes_order.py`.

## Frontend visualization

### The flavours route and `SunburstChart`

`/flavours` is the dedicated flavour-exploration page. Its `+page.ts` loader calls `/v1/tasting-note-categories` (forwarding all URL filter parameters) and returns the grouped `categories` plus `metadata`. The page renders a `SunburstChart` — an interactive D3-based flavour wheel where:

- The innermost ring is the primary category.
- The middle ring is the secondary category.
- The outer ring is the tertiary category, with individual tasting notes as leaves.

`transformToSunburstData` (`lib/utils/sunburstDataTransform.ts`) builds the hierarchical tree from the flat API response. It flattens any `"General"` placeholder node directly into its parent, caps the leaf count per tertiary node at 10 (`TASTING_NOTE_THRESHOLD`), and buckets the remainder under an `isOther`-flagged `"Other"` node (or attaches a lone remainder directly). D3 sums parent values from the leaves.

The chart supports click-to-zoom into a category, pinch-to-zoom and pan on mobile, double-tap to reset, and hover tooltips. Clicking a tasting-note leaf calls `onTastingNoteClick`, which adds the note to the page's search filters. When the `flavourImagesEnabled` setting is on (disabled on mobile), hovering a note fetches and displays a matching flavour painting via the `flavourImageService`.

The page uses a canonical `FLAVOUR_CATEGORY_ORDER` (in `lib/utils.ts`) for consistent display ordering, and `getFlavourCategoryHexColor` assigns each primary category a stable hex colour (e.g. `Fruity` → `#f43f5e`, `Cocoa` → `#92400e`, `Floral` → `#d946ef`).

### `FlavourProfileDonut` on the roaster page

`FlavourProfileDonut.svelte` is a simpler donut chart shown on the roaster detail page. It takes a `categories` array of `{primary_category, count, percentage}` (the `flavour_categories` field of the roaster detail response) and renders a `layerchart` pie chart with callout labels. Slices below 2% hide their labels to avoid overlap; hovering a slice force-shows its label and dims the rest. The centre shows the total note count.

The roaster detail endpoint computes `flavour_categories` by joining the roaster's beans' tasting notes to `tasting_notes_categories`, **excluding** `Taste Basics`, `Mouthfeel`, and `Amplitude` so the profile reflects actual flavour descriptors, and only builds the profile when there are at least 3 categorised flavour notes. Each category's percentage is its share of that roaster's categorised notes.

### Guided tasting wizard

The guided tasting feature (`lib/components/tasting/TastingWizard.svelte` and `lib/tasting/conversation.ts`) is a conversational, wizard-like interface for users to record their own sensory appraisal of a bean. It uses the same SCA flavour lexicon as its category backbone, with category-specific guided questions, defect mappings (phenolic, rubbery, etc. mapped to SCA standards), and sensory intensity scales (acidity, sweetness, bitterness, mouthfeel, body). `mergeDynamicFlavours` merges live note-frequency data from the `/v1/tasting-note-categories` API into the wizard's hardcoded skeleton, so the chips a user sees reflect the actual prevalence of each note in the database. The wizard's state machine runs `basics → overview → category → mouthfeel → summary`, and sessions are persisted client-side in IndexedDB via Dexie. See `docs/GUIDED_TASTING_PLAN.md` in the repository for the design rationale.

## Relationship to processing methods

A coffee's processing method (washed, natural, honey, anaerobic, etc.) is a primary driver of its flavour profile — natural-process coffees tend toward fruity/fermented notes, washed toward clean acidity, and so on. The tasting-note taxonomy is therefore a natural companion to the [Processing Methods](processing-methods.md) concept: process determines the flavour direction, and the categorization taxonomy described here is how Kissaten makes that direction searchable and visualizable.

## Related pages

- [AI Pipeline](../ai/ai-pipeline.md) — the broader AI module landscape this categorizer/splitter belongs to.
- [Backend API & Database](../api/backend-api.md) — the FastAPI surface and DuckDB layer hosting the endpoints above.
- [Processing Methods](processing-methods.md) — process determines flavour profile.
- [Data Model](../data/data-model.md) — the `CoffeeBean` schema and `tasting_notes_categories` table.
- [Name Mappings & Canonical Reference Data](../data/name-mappings.md) — the lexicon and categorized CSV as canonical reference files.
