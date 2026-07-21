---
type: "Feature"
title: "Roaster Uniqueness Report"
description: "Multi-dimensional statistical analysis that identifies where a roaster most over-indexes vs the global average across flavour, origin, process, and varietal dimensions. Computed on the roaster detail endpoint and rendered as a headline sentence plus secondary chips on the frontend."
tags: ["uniqueness", "roaster", "statistics", "lift", "percentile"]
timestamp: "2025-01-15T00:00:00Z"
---

# Roaster Uniqueness Report

## Overview

The uniqueness report answers the question: *"What makes this roaster stand out from the crowd?"* It compares a single roaster's category distribution across four dimensions — flavour, origin, process, and varietal — against the global average of all roasters in the database. The result is surfaced on the [roaster detail page](../frontend/frontend.md) as a headline sentence ("What Makes Them Unique") plus secondary dimension chips.

The feature was introduced in commit `a90e6ce` ("Added new roasters plus improvements to the roaster page") and lives entirely in the backend computation layer plus a frontend rendering layer.

## Data Flow

```
Roaster detail request
  → _compute_uniqueness_report(conn, roaster_name, flavour_total)
    → For each dimension: query DuckDB for per-roaster category counts
    → _best_uniqueness_insight(...) per dimension
    → Pick top insight (highest percentile, tie-broken by lift, then sample size)
    → UniquenessReport(top=..., by_dimension={...})
  → RoasterDetailResponse.uniqueness
  → Frontend +page.svelte renders headline + chips
```

## Backend Implementation

### Source Files

| File | Role |
|---|---|
| `src/kissaten/api/main.py` (lines ~1352–1713) | `_best_uniqueness_insight()`, `_aggregate_categorised_counts()`, `_compute_uniqueness_report()`, category display-label maps |
| `src/kissaten/schemas/roaster_models.py` | `UniquenessInsight`, `UniquenessReport`, `RoasterDetailResponse.uniqueness` field |
| `src/kissaten/api/main.py` (~line 3062) | Call site: `uniqueness = _compute_uniqueness_report(conn, roaster_name, flavour_total)` inside the roaster detail endpoint |

### Core Algorithm: `_best_uniqueness_insight`

This is the statistical heart of the feature. For a single dimension (e.g. flavour), it:

1. **Builds per-roaster category counts**: a `dict[category, dict[roaster, count]]` where only roasters with a non-zero count appear.
2. **Builds per-roaster totals**: a `dict[roaster, total]` used as the denominator.
3. **For each category**, computes:
   - **this_roaster_pct**: the roaster's share of beans/notes in this category (percentage of their total).
   - **global_pct**: the global share across all roasters for this category.
   - **lift**: signed difference `this_roaster_pct - global_pct` (in percentage points).
   - **percentile**: what percentage of roasters (that touch this category) have a lower share than this roaster.
4. **Filters** candidates through threshold gates (see below).
5. **Picks the best** candidate by highest percentile, tie-broken by lift.

### Threshold Gates

Every dimension must pass all of these to produce an insight:

| Threshold | Default | Purpose |
|---|---|---|
| `min_sample_size` | 3 | Roaster must have at least 3 beans/notes in this dimension's denominator |
| `min_lift` | 2.0 | The roaster's share must exceed the global average by more than 2 percentage points |
| `min_percentile` | 60.0 | The roaster must rank above 60% of roasters that touch this category |
| `min_this_pct` | 10.0 | The standout category must represent ≥10% of the roaster's total for that dimension |
| `min_this_count` | 3 | Absolute floor: the category must have ≥3 beans/notes — the effective percentage floor is `max(min_this_pct, min_this_count / this_total * 100)` |

The `min_this_pct` / `min_this_count` interaction is designed so that small catalogues are not penalised by a fixed percentage alone — a roaster with 10 beans where 3 are from Ethiopia (30%) passes, while a roaster with 100 beans where 3 are from Ethiopia (3%) does not. The `max()` of the two ensures both floors are enforced.

### Four Dimensions

Each dimension has its own SQL query and categorization approach:

#### 1. Flavour
- **Denominator**: categorised tasting notes (excludes `Taste Basics`, `Mouthfeel`, `Amplitude` categories).
- **Category**: `tasting_notes_categories.primary_category` (e.g. "Stone Fruit", "Citrus").
- **Display label**: the category name directly (e.g. "Stone Fruit").
- **Link**: `None` (no dedicated route for flavour categories).
- **SQL**: joins `coffee_beans` → `unnest(tasting_notes)` → `tasting_notes_categories`.

#### 2. Origin
- **Denominator**: origin rows with a non-empty `country`.
- **Category**: ISO alpha-2 country code (e.g. "ET", "CO").
- **Display label**: resolved to full country name via `country_codes` table.
- **Link**: `/origins/{code.lower()}`.
- **SQL**: joins `coffee_beans` → `origins`.

#### 3. Process
- **Denominator**: origin rows with a non-empty `process_common_name` (falls back to `process`).
- **Category**: the specific `process_common_name` (e.g. "Washed", "Anaerobic Natural") — **not** the broad category cluster from `categorize_process`. Individual common names are more interesting as standouts than "Anaerobic & Carbonic" would be.
- **Display label**: the process name directly.
- **Link**: `/processes/{normalize_process_name(name)}`.
- **SQL**: joins `coffee_beans` → `origins`, using `COALESCE(NULLIF(process_common_name, ''), NULLIF(process, ''), '')`.

#### 4. Varietal
- **Denominator**: varietal mentions (from `origins.variety_canonical` array, falling back to `origins.variety`).
- **Category**: the specific canonical varietal name (e.g. "Geisha", "SL28", "Bourbon") — **not** the broad family cluster from `categorize_varietal`. Individual varietals are more interesting than "Bourbon Family" would be.
- **Display label**: the varietal name directly.
- **Link**: `/varietals/{normalize_varietal_name(name)}`.
- **SQL**: joins `coffee_beans` → `origins`, unnesting `variety_canonical` (or falling back to `[variety]`).

### Top Selection

After computing insights for all four dimensions, `_compute_uniqueness_report` picks the single strongest as `top`:

```python
top_dim = max(
    insights.keys(),
    key=lambda d: (
        insights[d].percentile,
        insights[d].lift,
        insights[d].sample_size,
    ),
)
```

Tie-breaking order: **percentile → lift → sample size** (more data = more trustworthy). The remaining dimensions (those that also passed thresholds) form `by_dimension`, **excluding** the top dimension so the headline and chip never duplicate each other.

### Category Display Label Maps

The `_PROCESS_CATEGORY_NAMES` and `_VARIETAL_CATEGORY_NAMES` dicts map internal slugs to display labels (e.g. `anaerobic_carbonic` → "Anaerobic & Carbonic"). These exist for consistency with the `/v1/processes` and `/v1/varietals` index pages, though the process and varietal dimensions use specific names rather than category slugs as their standout.

## Pydantic Models

### `UniquenessInsight`

```python
class UniquenessInsight(BaseModel):
    dimension: Literal["flavour", "origin", "process", "varietal"]
    primary_category: str    # raw key (flavour name, ISO code, process name, varietal name)
    display_label: str       # human-readable label for chips/headlines
    this_roaster_pct: float  # roaster's share in this category (0-100)
    global_pct: float        # global share (0-100)
    lift: float              # signed difference (percentage points)
    percentile: float        # % of roasters below this roaster's share
    sample_size: int         # beans/notes in the denominator
    link: Optional[str]      # site path to explore further
```

### `UniquenessReport`

```python
class UniquenessReport(BaseModel):
    top: Optional[UniquenessInsight]              # strongest standout across all dimensions
    by_dimension: Dict[str, UniquenessInsight]    # per-dimension winners (excl. top dimension)
```

`top` is `None` when no dimension passes all thresholds. `by_dimension` only includes dimensions that passed and are not the top dimension.

### `RoasterDetailResponse`

The `uniqueness` field is `Optional[UniquenessReport]` — `None` when no dimension qualifies, meaning the "What Makes Them Unique" section is simply not rendered.

## Frontend Rendering

### Source Files

| File | Role |
|---|---|
| `frontend/src/routes/(main)/roasters/[roaster_name]/+page.ts` | Loads `detail.uniqueness` from the API response, passes it as `data.uniqueness` |
| `frontend/src/routes/(main)/roasters/[roaster_name]/+page.svelte` | `uniquenessSentence()`, `dimensionIcon()`, headline + chip rendering |
| `frontend/src/lib/api.ts` (lines ~118–144) | TypeScript `uniqueness` type definition on `RoasterDetailResponse` |

### Headline ("What Makes Them Unique")

When `uniqueness.top` is non-null, the page renders a "What Makes Them Unique" section with:

1. **Headline sentence**: dimension-aware phrasing via `uniquenessSentence()`.
   - flavour: `"{name}'s tasting notes skew {label} — more so than {percentile}% of roasters."`
   - origin: `"{name}'s sourcing skews {label} — more so than {percentile}% of roasters."`
   - process: `"{name}'s processing skews {label} — more so than {percentile}% of roasters."`
   - varietal: `"{name}'s varietals skew {label} — more so than {percentile}% of roasters."`
2. **Detail sentence**: includes this roaster's %, global %, lift, and sample size.

The standout label is rendered in **bold** in the headline. Flavour/process labels are lowercased inside the detail sentence; origin/varietal labels keep their proper-case spelling.

### Secondary Chips

Dimensions that also passed thresholds (but were not the top) render as chips below the headline. Each chip:
- Shows the dimension icon (via `dimensionIcon()`): `Sparkles` (flavour), `MapPin` (origin), `Droplets` (process), `Leaf` (varietal).
- Links to the relevant exploration page (`/origins/et`, `/processes/washed`, `/varietals/geisha`, etc.) when `link` is non-null.
- Flavour dimension chips do not link (no dedicated route exists for flavour categories).

### Dimension Nouns

The `DIMENSION_NOUN` map provides the grammatical noun for each dimension:
- flavour → "tasting notes"
- origin → "beans"
- process → "beans"
- varietal → "varietal mentions"

## Edge Cases and Design Decisions

- **Small catalogues**: roasters with fewer than 3 beans/notes in a dimension are excluded entirely (`min_sample_size`). The absolute count floor (`min_this_count=3`) prevents a single bean from becoming a "standout."
- **No qualifying dimensions**: when no dimension passes all thresholds, `top` is `None` and the entire uniqueness section is hidden on the frontend.
- **Process/varietal specificity**: the implementation deliberately uses specific common names (e.g. "Anaerobic Natural") rather than broad category clusters (e.g. "Anaerobic & Carbonic") because individual names are more interesting and actionable as standouts. This also enables direct linking to the `/processes/[slug]` and `/varietals/[slug]` routes.
- **Percentile semantics**: the percentile is computed only over roasters that have a non-zero count for the category — roasters with zero count for that category are excluded (not counted as "below"). This matches the original flavour-only implementation's semantics.
- **No reciprocal links**: the uniqueness report is read-only output from the roaster detail endpoint. It does not write back to DuckDB or modify roaster records.
- **Excluded flavour categories**: `Taste Basics`, `Mouthfeel`, and `Amplitude` are excluded from the flavour dimension because they are generic categories that don't differentiate roasters.

## Change Guidance

When modifying the uniqueness report:

1. **Thresholds**: the `min_sample_size`, `min_lift`, `min_percentile`, `min_this_pct`, and `min_this_count` defaults are tuned for the current catalogue of ~150 roasters. Changing them will affect how many roasters have a uniqueness report at all — lowering thresholds increases coverage but may produce less meaningful standouts.
2. **Adding a new dimension**: add a new block in `_compute_uniqueness_report`, following the existing pattern (SQL query → `per_roaster_category_counts` + `per_roaster_totals` → `_best_uniqueness_insight()`). Add the dimension to the `Literal` type in `UniquenessInsight`, the `DIMENSION_NOUN` map and `uniquenessSentence()` switch in the frontend, and `dimensionIcon()`.
3. **Category label maps**: if you add or rename process/varietal category slugs, update `_PROCESS_CATEGORY_NAMES` and `_VARIETAL_CATEGORY_NAMES` to keep chip labels consistent with the index pages.
4. **Performance**: the uniqueness computation runs on every roaster detail request (it is not cached). Each dimension issues 1–2 SQL queries against DuckDB. For the current catalogue size this is fast, but if the roaster count grows significantly, consider caching the global aggregates.
5. **Tests**: there are no dedicated uniqueness tests in the test suite. When adding or modifying the algorithm, add tests in `tests/` that verify threshold gating, top selection tie-breaking, and the `None` return when no dimensions qualify.
