# Geographical Data Implementation

This document describes the technical implementation of the geographical hierarchy (Country -> Region -> Farm) in Kissaten. It covers data normalization, deduplication, aggregation logic, and frontend presentation.

## Hierarchy Overview

Data is organized in a three-level hierarchy:
1.  **Country**: Identified by ISO 3166-1 alpha-2 codes (e.g., `CO` for Colombia).
2.  **Region**: Sub-national administrative areas (e.g., `Caldas`, `Antioquia`).
3.  **Farm**: Specific production sites, which may have associated producers.

## Backend Implementation

### Data Normalization & Deduplication

A major challenge in the dataset is the variation in naming for the same geographical entity (e.g., "Finca Milan" vs "Finca Milán"). To resolve this, we use **normalization-based grouping**.

#### Python Normalization Functions
We implemented `normalize_region_name` and `normalize_farm_name` in `src/kissaten/api/main.py`. These functions:
1.  Normalize Unicode to NFD form.
2.  Remove diacritics (accents).
3.  Convert to lowercase.
4.  Remove non-alphanumeric characters.
5.  Collapse whitespace into single hyphens.

#### DuckDB Integration
These Python functions are registered as custom DuckDB functions using `conn.create_function`. This allows the SQL engine to call them directly during queries:

```sql
SELECT normalize_farm_name(farm), count(*)
FROM origins
WHERE country = 'CO'
GROUP BY 1
```

#### Selection Logic (`arg_max`)
When deduplicating farms in the Region Detail view, we use DuckDB's `arg_max` to select the "best" display name (usually the one with the most information or the longest string) while grouping by the normalized name.

### Canonicalization

To ensure consistency in tasting notes, varietals, and processing methods, we prioritize "canonical" fields:
-   **Varietals**: We use `variety_canonical` (an array field) instead of the raw `variety` string when available.
-   **Processing**: We use `COALESCE(NULLIF(o.process_common_name, ''), o.process)` to prioritize standardized process names.

### Aggregation

Statistics (bean counts, roaster counts, elevation ranges) are aggregated at each level of the hierarchy using SQL window functions and CTEs to ensure high performance even with large datasets.

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
