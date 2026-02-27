# Geographical Data Implementation

This document describes the technical implementation of the geographical hierarchy (Country -> Region -> Farm) in Kissaten. It covers data normalization, deduplication, aggregation logic, and frontend presentation.

## Hierarchy Overview

Data is organized in a three-level hierarchy:
1.  **Country**: Identified by ISO 3166-1 alpha-2 codes (e.g., `CO` for Colombia).
2.  **Region**: Sub-national administrative areas (e.g., `Caldas`, `Antioquia`).
3.  **Farm**: Specific production sites, which may have associated producers.

## Backend Implementation

### Data Normalization & Deduplication

A major challenge in the dataset is the variation in naming for the same geographical entity (e.g., "Finca Milan" vs "Finca Milán"). To resolve this, we use **normalization-based grouping** with precalculated normalized values stored in the database.

#### Python Normalization Functions
We implemented `normalize_region_name` and `normalize_farm_name` in `src/kissaten/api/db.py`. These functions:
1.  Normalize Unicode to NFD form.
2.  Remove diacritics (accents).
3.  Convert to lowercase.
4.  Remove non-alphanumeric characters.
5.  Collapse whitespace into single hyphens.

#### Database Schema
The `origins` table includes pre-calculated normalized columns:
-   `region_normalized`: Pre-calculated normalized region name
-   `farm_normalized`: Pre-calculated normalized farm name

These values are calculated during data loading (in `load_coffee_data()`) for optimal query performance.

#### DuckDB Integration
The normalization functions are registered as custom DuckDB functions using `conn.create_function` for use during data loading and for normalizing search queries:

```sql
SELECT farm_normalized, count(*)
FROM origins
WHERE country = 'CO'
GROUP BY farm_normalized
```

#### Selection Logic (`arg_max`)
When deduplicating farms in the Region Detail view, we use DuckDB's `arg_max` to select the "best" display name (usually the one with the most information or the longest string) while grouping by the normalized name.

### Canonicalization

To ensure consistency in tasting notes, varietals, and processing methods, we prioritize "canonical" fields:
-   **Varietals**: We use `variety_canonical` (an array field) instead of the raw `variety` string when available.
-   **Processing**: We use `COALESCE(NULLIF(o.process_common_name, ''), o.process)` to prioritize standardized process names.

### Canonical Region Slug Grouping

This is the most critical invariant in the origin endpoints. When regions are geocoded, their `state_canonical` (e.g. "Chiriquí") may differ from the raw `region` string (e.g. "Boquete", "Volcán"). Multiple raw regions can map to the same canonical state. The system must ensure that:

1.  **All endpoints use the same grouping expression** for region identity:
    ```sql
    COALESCE(normalize_region_name(o.state_canonical), o.region_normalized)
    ```
    This expression computes the "effective slug" — the canonical slug when geocoded, falling back to the raw slug otherwise.

2.  **The regions-list** (`GET /v1/origins/{country}/regions`) uses this expression in its `GROUP BY` clause, merging all raw variants into a single entry per canonical state.

3.  **The region-detail** (`GET /v1/origins/{country}/{region_slug}`) and **farm-detail** (`GET /v1/origins/{country}/{region_slug}/{farm_slug}`) use the **same** COALESCE expression in their `WHERE` clauses. This is essential — using `OR` (e.g. `normalize_region_name(state_canonical) = ? OR region_normalized = ?`) would cause "slug leaks" where rows whose raw slug matches a different canonical group get incorrectly included.

4.  **Display names** use `MODE()` with a `FILTER` clause to prefer the canonical name:
    ```sql
    COALESCE(
        MODE(o.state_canonical) FILTER (WHERE o.state_canonical IS NOT NULL AND o.state_canonical != ''),
        MODE(o.region)
    ) as region_name
    ```

#### Example: Panama

```
region='Boquete'  → region_normalized='boquete'  → state_canonical='Chiriquí' → effective_slug='chiriqui'
region='Volcán'   → region_normalized='volcan'    → state_canonical='Chiriquí' → effective_slug='chiriqui'
```

Both beans appear under a single "Chiriquí" entry with slug `chiriqui` in the regions list. The raw slugs `boquete` and `volcan` are no longer independently accessible.

#### Why NOT to use OR-based filters

A previous implementation used:
```sql
WHERE normalize_region_name(o.state_canonical) = ? OR o.region_normalized = ?
```

This caused a data leak. For example, querying `sidama-bensa`:
- Rows with `region='Sidama Bensa'` have `region_normalized='sidama-bensa'` but `state_canonical='Sidama'` (canonical slug `'sidama'`).
- The `OR` clause matched these rows on `region_normalized='sidama-bensa'`, but they actually belong to the `'sidama'` canonical group.
- Result: 55 beans instead of the correct 7.

The COALESCE-based filter correctly evaluates each row's effective slug and only matches rows that truly belong to the requested group.

#### Cross-Region Data Leak Prevention

Region-detail sub-queries (stats, farms, varietals, processes, elevation) that join `origins o ON t.bean_id = o.bean_id` **must** also include the region filter (`AND {region_filter_sql}` with params). Without this, a bean with origins in multiple regions would leak data from other regions into the response.

All 6 sub-query joins in region-detail include this filter:
- Stats aggregation
- Known farms list
- Unknown farms count
- Varietal distribution
- Process distribution
- Elevation distribution

### Aggregation

Statistics (bean counts, roaster counts, elevation ranges) are aggregated at each level of the hierarchy using SQL window functions and CTEs to ensure high performance even with large datasets.

### Farm Count Expression

Farm counts must use consistent expressions across list and detail endpoints:
```sql
COUNT(DISTINCT COALESCE(o.farm_canonical, o.farm_normalized))
    FILTER (WHERE o.farm IS NOT NULL AND o.farm != '')
```

Key points:
- Use `farm_normalized` (not raw `farm`) as the fallback in COALESCE for consistent deduplication.
- The `FILTER` clause is required to exclude rows with NULL or empty farm names from the count.

## Frontend Implementation

### Normalization Parity
The frontend (`frontend/src/lib/api.ts` and `frontend/src/lib/utils.ts`) implements parallel normalization logic. This ensures that URL slugs generated in the UI (e.g., for breadcrumbs or links) match the slugs the Backend expects for filtering.

### Themed Insight Cards
Visual consistency is maintained using "Insight Cards" with standardized color themes:
-   **Roasters**: `varietal-detail-insight-card-green`
-   **Varietals**: `varietal-detail-insight-card-blue`
-   **Processing**: `varietal-detail-insight-card-orange`
-   **Tasting Notes**: `varietal-detail-insight-card-purple`

These themes include specific dark-mode shadow and border configurations defined in `app.css`.

### Entity Linking
Every geographical entity is interconnected:
-   **Breadcrumbs**: Allow stepping back up the hierarchy.
-   **Insight Items**: Clicking a varietal or process in an origin view navigates to the dedicated `/varietals/{slug}` or `/processes/{slug}` page.
-   **Search Integration**: Tasting notes link to the search page pre-filtered by that specific flavor profile and geographical context.

## Models & Schemas

The Pydantic models in `src/kissaten/schemas/geography_models.py` define the response structures for:
-   `CountryDetailResponse`
-   `RegionDetailResponse`
-   `FarmDetailResponse`

These models ensure that aggregated data (Top Varieties, Common Notes, etc.) is typed and validated before reaching the frontend.

## API Endpoints

The origin endpoints form a strict hierarchy. Consistency invariants must hold across all levels:

| Endpoint | Purpose | Key Grouping |
|---|---|---|
| `GET /v1/origins` | Country list | `o.country` |
| `GET /v1/origins/{cc}` | Country detail | `WHERE o.country = ?` |
| `GET /v1/origins/{cc}/regions` | Region list | `GROUP BY COALESCE(normalize_region_name(o.state_canonical), o.region_normalized)` |
| `GET /v1/origins/{cc}/{slug}` | Region detail | `WHERE ... COALESCE(...) = ?` |
| `GET /v1/origins/{cc}/{slug}/{farm}` | Farm detail | Same region filter + farm filter |

### Consistency Invariants

These invariants are enforced by the test suite (`tests/test_origin_hierarchy_counts.py`, `tests/test_region_name_consistency.py`, `tests/test_canonical_slug_grouping.py`):

1.  **Country list ↔ detail**: `bean_count` and `roaster_count` in the list must equal `total_beans` and `total_roasters` in the detail.
2.  **Region list ↔ detail**: `bean_count` and `farm_count` in the list must equal `total_beans` and `total_farms` in the detail.
3.  **No duplicate region names**: The regions list must have unique `region_name` values.
4.  **Name round-trip**: `normalize_region_name(region_name)` from the list must resolve to the same `region_name` in the detail.
5.  **No region exceeds country**: No region's `bean_count` exceeds its country's `total_beans`.
6.  **Farm list matches stats**: Length of `top_farms` (excluding "Unknown Farm") equals `total_farms`.
7.  **Farm bean coverage**: Sum of farm `bean_count` values ≥ region `total_beans`.
8.  **Canonical slug exclusivity**: Raw slugs subsumed into a canonical group do not appear as independent entries.
9.  **No slug leak**: Querying a subsumed raw slug does not return data from the canonical group.

## Testing

### Test Files for Geographical Data

| File | Tests | Purpose |
|---|---|---|
| `tests/test_region_name_consistency.py` | 7 | Region names match between list/detail; no duplicates; canonical names used; bean/farm counts match |
| `tests/test_origin_hierarchy_counts.py` | 12 | Cross-level count consistency (country↔region↔farm); internal stat consistency |
| `tests/test_canonical_slug_grouping.py` | 7 | Canonical slug merging; raw slug inaccessibility; no slug leak; farm-detail respects grouping |
| `tests/test_origins_api.py` | — | General origin API endpoint tests |
| `tests/test_invalid_regions.py` | — | Handling of invalid/malformed region inputs |

### Common Pitfalls When Modifying Origin Endpoints

1.  **Always use the COALESCE expression** for region identity — never match on `region_normalized` alone when geocoded data exists.
2.  **Add `{region_filter_sql}` to ALL sub-query joins** in region-detail. Missing it on even one sub-query causes cross-region data leaks.
3.  **Keep farm count expressions identical** between list and detail (`COALESCE(farm_canonical, farm_normalized)` with `FILTER`).
4.  **Watch out for DuckDB lock conflicts** when running tests — the AI search cache at `data/ai_search_cache.duckdb` can hold locks from stale processes. Kill them with `kill <PID>` before re-running tests.
5.  **The `MODE()` aggregate is deterministic** for a given dataset but its result depends on frequency. Use it consistently with the same `FILTER` clause everywhere.
