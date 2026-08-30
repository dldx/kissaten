---
type: design
title: Faceted Filtering System
description: Design documentation for the faceted filtering system — the SearchFilters component, the full filter taxonomy (origin, roaster, process, varietal, roast level, roast profile, price, weight, elevation, in-stock, decaf, single-origin, tasting-kit), URL-driven state management, and the /v1/search API that powers it.
tags: [faceted-filtering, search, url-driven-state, svelte, api, filter-taxonomy, faceted-search]
verified:
  - by: openwiki/0.4.3
    at: 2026-08-29T13:59:13.975Z
sources:
  - id: openwiki-source-35aacac0c5c266af35e7486b
    resource: repo://frontend/src/lib/components/search/FilterTags.svelte
  - id: openwiki-source-24225342590a035226d3afa6
    resource: repo://frontend/src/lib/components/search/SearchFilters.svelte
  - id: openwiki-source-aa05fef58ff2bd104cd578cc
    resource: repo://frontend/src/lib/components/search/SearchResults.svelte
  - id: openwiki-source-b6ca501eb95744c3fa64f5ec
    resource: repo://frontend/src/lib/components/search/SmartSearch.svelte
  - id: openwiki-source-b9b678dc2f547df4edcc8159
    resource: repo://frontend/src/lib/stores/search.ts
  - id: openwiki-source-46571e66ddc30a08b064748c
    resource: repo://frontend/src/lib/utils/roasterLocations.ts
  - id: openwiki-source-50221da732cef6feab6d8b95
    resource: repo://frontend/src/routes/(main)/%2Blayout.ts
  - id: openwiki-source-be5ca84f39efd71f618e9a90
    resource: repo://frontend/src/routes/(main)/search/%2Bpage.svelte
  - id: openwiki-source-6fefffdc53af3312d4de54c1
    resource: repo://frontend/src/routes/(main)/search/%2Bpage.ts
  - id: openwiki-source-9735fcc3e14d5d9974206d6d
    resource: repo://src/kissaten/api/main.py
  - id: openwiki-source-0d95f608f6d7d340f981a2cc
    resource: repo://src/kissaten/schemas/api_models.py
  - id: openwiki-source-dda104ebf8fb951b79d769b0
    resource: repo://src/kissaten/schemas/search.py
generated: { by: "openwiki/0.4.3", at: "2026-08-29T13:59:13.975Z" }
---

# Faceted Filtering System

Kissaten's catalogue spans thousands of coffee beans scraped from roasters worldwide. Users arrive with specific preferences — a particular origin country, a roast level, a price band, a process method — and need to narrow the results along several of these dimensions at once. The faceted filtering system lets users refine results along multiple independent dimensions simultaneously, each mapped to a concrete domain concept, with the full filter state encoded in the URL so that any query is shareable and server-rendered.

The system spans three layers: a SvelteKit search route that performs SSR data loading from URL parameters, a `searchStore` that manages client-side state and orchestrates API calls, and the FastAPI `/v1/search` endpoint that compiles filters into parameterised DuckDB SQL. The UI is composed from three components — `SearchFilters` (the faceted input panel), `FilterTags` (the active-filter display), and `SearchResults` (the result grid plus sort controls) — all driven by a single shared store.

## Architecture overview

<!-- openwiki: mermaid parse failed and this diagram was converted to a text fence so it does not break rendering. Fix the diagram source and restore the mermaid fence. Parser error: Heuristic: an unescaped angle bracket inside a label breaks rendering; rephrase the label. -->
```text
flowchart TD
    URL["URL query params<br/>/search?q=...&origin=ET&roast_level=Light&min_price=15"]
    PT["+page.ts load<br/>parses URL → SearchParams → api.search()"]
    SS["searchStore<br/>(Svelte writable)"]
    SF["SearchFilters.svelte<br/>faceted input panel"]
    FT["FilterTags.svelte<br/>active-filter display"]
    SR["SearchResults.svelte<br/>result grid + sort controls"]
    API["/v1/search endpoint<br/>FastAPI"]
    DB["DuckDB<br/>build_coffee_bean_filters()"]

    URL --> PT
    PT -->|server data| SS
    SS -->|bind:filter props| SF
    SF -->|onSearch callback| SS
    SS -->|performNewSearch| API
    SS -->|updateURL| URL
    API -->|SQL conditions + scoring| DB
    DB -->|APISearchResult[]| API
    API -->|APIResponse| SS
    SS -->|results| SR
    SR -->|handleRemoveFilter| SS
    FT -->|onRemoveFilter / onClearAll| SR
```

## Filter taxonomy and domain concept mapping

Each facet in the `SearchFilters` component maps to a domain concept documented elsewhere in the wiki. The filters fall into several categories: text search, categorical filters (multi-select or single-select), range filters, and boolean/tri-state filters.

| Filter | Component field | URL parameter(s) | API parameter | Domain concept |
|---|---|---|---|---|
| Search query | `searchQuery` | `q` | `query` | General text (name, description, tasting notes) |
| Tasting notes query | `tastingNotesQuery` | `tasting_notes_query` | `tasting_notes_query` | [Tasting note taxonomy](../concepts/tasting-note-taxonomy.md) |
| Roaster | `roasterFilter` (multi) | `roaster` (repeated) | `roaster` | [Roaster exploration](../design/roaster-exploration.md) |
| Roaster location | `roasterLocationFilter` (multi) | `roaster_location` (repeated) | `roaster_location` | [Origin geography](../concepts/origin-geography.md) |
| Coffee origin (country) | `originFilter` (multi) | `origin` (repeated) | `origin` | [Origin geography](../concepts/origin-geography.md) |
| Region | `regionFilter` | `region` | `region` | [Origin geography](../concepts/origin-geography.md) |
| Producer | `producerFilter` | `producer` | `producer` | [Origin geography](../concepts/origin-geography.md) |
| Farm | `farmFilter` | `farm` | `farm` | [Origin geography](../concepts/origin-geography.md) |
| Roast level | `roastLevelFilter` | `roast_level` | `roast_level` | [Roast levels & profiles](../concepts/roast-levels-profiles.md) |
| Roast profile | `roastProfileFilter` | `roast_profile` | `roast_profile` | [Roast levels & profiles](../concepts/roast-levels-profiles.md) |
| Process | `processFilter` | `process` | `process` | [Processing methods](../concepts/processing-methods.md) |
| Variety | `varietyFilter` | `variety` | `variety` | [Varietals](../concepts/varietals.md) |
| Price range | `minPrice` / `maxPrice` | `min_price` / `max_price` | `min_price` / `max_price` | [Price transparency](../concepts/price-transparency.md) |
| Weight range | `minWeight` / `maxWeight` | `min_weight` / `max_weight` | `min_weight` / `max_weight` | Retail packaging |
| Min bag size | `minLargeWeight` | `min_large_weight` | `min_large_weight` | Bulk pricing (see below) |
| Elevation range | `minElevation` / `maxElevation` | `min_elevation` / `max_elevation` | `min_elevation` / `max_elevation` | [Origin geography](../concepts/origin-geography.md) |
| In stock only | `inStockOnly` | `in_stock_only` | `in_stock_only` | Retail availability |
| Decaf | `isDecaf` (tri-state) | `is_decaf` | `is_decaf` | [Decaffeination](../concepts/decaffeination.md) |
| Single origin | `isSingleOrigin` (tri-state) | `is_single_origin` | `is_single_origin` | [Origin geography](../concepts/origin-geography.md) |
| Tasting kit | `isTastingKit` | `is_tasting_kit` | `is_tasting_kit` | Retail product type |
| Sort | `sortBy` / `sortOrder` | `sort_by` / `sort_order` | `sort_by` / `sort_order` | Result ordering |

### Boolean search syntax

The text-based filters (`searchQuery`, `tastingNotesQuery`, `roastLevelFilter`, `processFilter`, `varietyFilter`, `regionFilter`, `producerFilter`, `farmFilter`) all support a shared boolean query syntax compiled server-side by `parse_boolean_search_query_for_field()`. The `SearchFilters` component surfaces this syntax with inline help text:

- `|` — OR: `chocolate|caramel`
- `&` — AND: `washed&natural`
- `!` or `NOT` — negation: `chocolate&!bitter`
- `*` and `?` — wildcard matching: `ge*sha`
- `()` — grouping: `berry&(lemon|lime)`
- `"quoted text"` — case-insensitive exact match

Each term is compiled into DuckDB `ILIKE` predicates (or `=` for exact matches) with `strip_accents()` applied when the field is pre-computed with an unaccented variant. This lets users search across diacritics (e.g. `Gechat` matching `Geisha`) and combine terms arbitrarily.

## URL-driven state and the SSR load flow

The search page lives at `/search` under the `(main)` route group. Its state is entirely URL-driven, which makes queries shareable, bookmarkable, and SSR-friendly. The flow has two phases: an initial server-side load and subsequent client-side updates.

### Server-side load: `+page.ts`

The `+page.ts` `load` function runs on both server and client. It reads every search parameter from `url.searchParams`, builds a `SearchParams` object, and calls `api.search(params, fetch)` — using SvelteKit's injected `fetch` so the call works server-side. The response is returned as `data` and includes:

- `searchResults` — the first page of `CoffeeBean[]` (already fetched for SSR)
- `totalResults`, `metadata`, `totalPages`
- `searchParams` — all parsed filter values echoed back so the store can rehydrate
- `originOptions`, `allRoasters`, `roasterLocationOptions` — dropdown option lists loaded by the parent `+layout.ts`
- `searchError` — if the API returned a 400 (invalid filter values), the error message is returned as data rather than thrown, so the user can see the form and correct their input

A key behaviour: **roaster location defaults**. If no `roaster_location` URL parameter is present and `apply_location_defaults` is not `"false"`, the load function falls back to `parentData.userDefaults.roasterLocations` — the user's saved location preferences. The `searchStore.updateURL()` writes `apply_location_defaults=false` when the user clears location filters, preventing the defaults from silently re-applying.

### Client-side updates: `searchStore`

The `searchStore` (a Svelte `writable` store created by `createSearchStore()`) is the single source of truth after hydration. `+page.svelte` calls `searchStore.set()` with the server-loaded data on mount, then all subsequent filter changes flow through the store:

1. **User changes a filter** in `SearchFilters` (e.g. selects a country). The two-way `bind:` on each filter prop propagates the change to `searchStore`.
2. **`onSearch` callback** fires — this is `searchStore.performNewSearch`, which resets page to 1, calls `buildSearchParams(1)`, and issues `api.search(params)`.
3. **`updateURL()`** is called after the API response, constructing a `URLSearchParams` from the current state and calling `goto(newUrl, { replaceState: true, noScroll: !scrollToTop })`. URL updates are debounced at 100ms to prevent rapid navigation when multiple filters change in quick succession.
4. **`loadMore()`** increments the page and appends results for infinite scroll, with a duplicate-id guard that deduplicates incoming beans by `id` to prevent Svelte `{#each}` reconciliation errors from non-deterministic pagination on ties.

The `clearFilters()` method resets every filter field to its empty/default value and triggers a new search. It is wired to both the `SearchFilters` clear button and the `SearchResults` no-results state.

### Dropdown options from the layout

The `originOptions` (country list), `allRoasters` (roaster names with `location_codes`), and `roasterLocationOptions` (hierarchical location codes like `XE` for Europe) are fetched once in the parent `+layout.ts` load function via three parallel API calls (`getCountries`, `getRoasters`, `getRoasterLocations`). These are passed as props to `SearchFilters` and `SearchResults`, then down to `FilterTags` for label resolution. The `SearchFilters` component also augments `originOptions` with any active `originFilter` values not already in the list, so filters set via URL (for countries with no beans in the database) still display correctly.

## The `/v1/search` endpoint

The backend endpoint is `GET /v1/search`, defined in `src/kissaten/api/main.py` as `search_coffee_beans()`. It is decorated with `@cached(cache=SimpleMemoryCache)` for in-memory response caching. The endpoint accepts all filter parameters as FastAPI `Query` parameters — many of them `list[str]` for multi-select filters like `roaster`, `roaster_location`, and `origin`.

### Filter compilation: `build_coffee_bean_filters()`

The `FilterParams` dataclass is the server-side container for all filter values. It is passed to `build_coffee_bean_filters(filter_params, use_scoring)`, which returns a `FilterResult` containing:

- `conditions` — SQL `WHERE` clauses for strict (non-relevance) mode, joined with `AND`
- `params` — the parameterised values for those conditions
- `score_components` — `CASE WHEN ... THEN weight ELSE 0 END` expressions for relevance mode
- `hard_conditions` / `hard_params` — filters that are always applied as `WHERE` regardless of mode (e.g. `in_stock_only`, `is_decaf`, `is_tasting_kit`, `requires_review`)
- `hard_params` — parameters for the hard conditions

The function handles each filter type differently:

- **Roaster** — `cb.roaster IN (?, ?, ...)` with the roaster names
- **Roaster location** — resolves location codes (e.g. `XE`) to matching roaster names via the scraper registry's `get_hierarchical_location_codes()`, then filters by roaster name
- **Origin (country)** — `EXISTS (SELECT 1 FROM origins o WHERE o.bean_id = cb.id AND o.country = ?)` for each country code, uppercased
- **Region/Producer/Farm** — `EXISTS` subqueries against the `origins` table, with normalised matching for simple queries (using `region_normalized`, `state_canonical_slug`, `farm_canonical`) and `ILIKE` fallback for complex boolean queries
- **Process** — checks both `o.process` and `o.process_common_name` in the origins table
- **Variety** — checks both `o.variety` and unnested `o.variety_canonical` array elements
- **Roast level** — in strict mode, a boolean-search filter on `cb.roast_level`; in scoring mode, a closeness function that scores exact match as 1.0, one level apart as 0.5, and two levels apart as 0.2 on a 0–5 roast scale
- **Roast profile** — boolean-search filter on `cb.roast_profile`
- **Price range** — uses `cb.price_usd` when currency conversion is requested, `cb.price` otherwise; the min/max values are converted from the target currency to USD before filtering
- **Weight range** — `cb.weight >= ? AND cb.weight <= ?`
- **Elevation range** — uses `MAX(o.elevation_max)` across all origins for the bean, so `min_elevation=1000` means the bean's peak elevation is at least 1000 m
- **Boolean filters** — `in_stock_only`, `is_decaf`, `is_tasting_kit`, and `is_single_origin` are compiled as hard or soft conditions depending on the filter type (see below)

### Hard vs soft conditions

Some filters are always applied as hard `WHERE` conditions regardless of sort mode, because showing beans that violate them would be misleading:

- `in_stock_only` — `cb.in_stock = true` (always hard)
- `is_decaf` — `cb.is_decaf = ?` (always hard, because showing the wrong caffeine status is never useful)
- `is_tasting_kit` — `cb.is_tasting_kit = ?` (always hard)
- `requires_review` / `include_unreviewed` — by default, rows with `requires_review = true` are hidden from public search via `REVIEW_HIDDEN_SQL`; only admin queries with `include_unreviewed=true` or explicit `requires_review` override this

In contrast, `is_single_origin` is a soft condition in scoring mode (it becomes a score component) but a hard `WHERE` filter in strict mode.

### Relevance scoring vs strict filtering

The endpoint has two modes determined by `sort_by`:

1. **Relevance mode** (`sort_by=relevance`): `build_coffee_bean_filters` is called with `use_scoring=True`. Each filter produces a `CASE WHEN ... THEN weight ELSE 0 END` score component. The score sum is computed in a CTE, and results are filtered with `WHERE score > 0` (any matching filter is sufficient). Results are ordered by `score DESC, name ASC, sb.id ASC`. The `max_possible_score` (the count of score components) is returned in `metadata` so the frontend can partition results into "matching" (score ≥ max) and "similar" (score < max) buckets.

2. **Strict mode** (any other sort): `build_coffee_bean_filters` is called a second time with `use_scoring=False`, producing `AND`-joined `WHERE` conditions that all filters must satisfy. Results are ordered by the user-selected sort field, with `sb.id ASC` as a deterministic tiebreaker to ensure stable pagination across pages.

The frontend's `SearchResults` component exploits `maxPossibleScore` to split the grid: when `sortBy === "relevance"`, beans with `score >= maxPossibleScore` are shown first in a "matching" section, then beans with `score < maxPossibleScore` in a "Similar beans" section below a visual separator.

### The `largest_bag` CTE and `price_large` sorting

Beans often come in multiple bag sizes with different prices, making per-gram or per-kilogram price comparisons non-trivial. The `price_large` sort option (labelled "Bulk price" in the UI) normalises this by sorting on the **price per kg of the largest available bag** for each bean.

Both the count query and the main query define a `largest_bag` CTE:

```sql
WITH largest_bag AS (
    SELECT DISTINCT ON (bean_id)
        bean_id,
        weight as lb_weight,
        price as lb_price,
        currency as lb_currency,
        price_per_kg_usd as lb_price_per_kg_usd
    FROM price_options
    WHERE price_per_kg_usd IS NOT NULL
    ORDER BY bean_id, weight DESC, price DESC
)
```

This selects, per bean, the price option with the largest weight (ties broken by highest price), exposing `lb_weight`, `lb_price`, `lb_currency`, and `lb_price_per_kg_usd`. The main query `LEFT JOIN`s this CTE so every result row carries its largest-bag pricing. The `price_large` sort maps to:

```sql
COALESCE(sb.lb_price_per_kg_usd, sb.price_usd / NULLIF(sb.weight, 0))
```

This sorts by the largest bag's price per kg, falling back to the default bag's price-per-gram if no `price_options` row exists. The `min_large_weight` filter (`AND cb.lb_weight >= ?`) further constrains results to beans whose largest bag is at least the specified weight, so the "Bulk price" sort only shows beans with meaningfully large bags.

When `price_large` is selected, the `SearchResults` component sets `useBulkPrice = true`, which is passed to `CoffeeBeanCard` so each card displays the largest-bag price instead of the default bag price.

## Response model: `APISearchResult`

The endpoint returns `APIResponse[list[APISearchResult]]`, where `APISearchResult` extends `APICoffeeBean` with search-specific fields:

- `date_added` — when the bean was first scraped/added
- `score` — the relevance score (float, only populated in relevance mode)
- `price_large_weight` — weight of the largest available bag in grams
- `price_large_price` — price of the largest bag in the user's requested currency
- `price_large_price_per_kg_usd` — normalised price per kg in USD

The response also includes `PaginationInfo` (page, per_page, total_items, total_pages, has_next, has_previous) and `metadata` (which carries `max_possible_score` for relevance partitioning). The `APIResponse` wrapper provides `success`, `data`, `message`, `pagination`, and `metadata` fields, with `success_response` and `error_response` class methods for consistent construction.

## Frontend components

### `SearchFilters` (~23 KB)

The faceted input panel. It renders every filter as an input control — `Svelecte` multi-selects for roaster, roaster location, and origin (with searchable, clearable, multiple); text `<Input>` elements with debounced search for query, tasting notes, region, producer, farm, roast level, process, and variety; numeric range inputs for price, weight, and elevation; radio buttons for the tri-state decaf and single-origin filters; and checkboxes for the roast profile (Filter/Espresso with an "Include omni roasts" sub-option). The roast profile filter has special logic: selecting "Filter" or "Espresso" always includes "Both" in the query (because "Both" beans are suitable for both), and optionally "Omni", producing a pipe-joined value like `Filter|Both|Omni`.

All filter props are `$bindable()`, so changes propagate up to the store via two-way binding. The `onSearch` callback (bound to `searchStore.performNewSearch`) is called on every `onChange`/`onfocusout`/Enter-key. Text inputs are debounced at 500ms to avoid firing a search on every keystroke.

The roaster filter options are dynamically narrowed by the selected roaster location: when `roasterLocationFilter` is non-empty, `filteredRoasterOptions` filters `allRoasters` to those whose `location_codes` include any selected location code, and the roaster `Svelecte` placeholder updates to show the location name(s).

### `FilterTags`

Displays the currently active filters as dismissible chips, each with an icon and label. It derives tags from every filter field — search query, individual tasting notes (parsed from the query string), each roaster, each roaster location (resolved to a display name like "Roasters in Europe"), each origin country (with flag and full name), roast level, roast profile, process, variety, price/weight/elevation ranges, min bag size, region, producer, farm, in-stock, tasting kit, decaf (showing "Decaf only" or "Caffeinated only"), and single-origin/blend. Each tag has an `onRemoveFilter(type, value)` handler that clears the specific filter value and triggers a new search, plus an `onClearAll` handler that resets everything. The `FilterTags` component is rendered in `SearchResults`, which wires the removal handler to mutate the bound store fields and call `onSearch`.

### `SearchResults` and sort controls

The result grid and sort controls. Sort options are defined as `sortLabels` with values matching the API's `sort_by` literal: `date_added` (Freshness), `relevance` (Relevance), `roaster`, `price`, `price_large` (Bulk price), `name`, `origin`, `region`, `elevation`, `variety`, `process`, `cupping_score` (Cupping Score), and `weight`. The sort order button cycles through `desc` → `asc` → `random` (with ArrowDown, ArrowUp, and Shuffle icons respectively). When `price_large` is selected, `minLargeWeight` is auto-set to `"1000"` if not already set, ensuring the bulk-price sort only surfaces beans with bags ≥ 1 kg.

The component also computes a `filterKey` — a `JSON.stringify` fingerprint of all filter values — which `SmartSearch` uses to detect whether the user has manually changed filters after an AI search (hiding the feedback/voting row when the filter state has drifted).

Results are rendered in an `InfiniteLoader` that triggers `onLoadMore` when the scroll sentinel approaches the viewport. Each result links to `"/roasters" + bean.bean_url_path`, the bean detail page (see [bean-detail-page.md](bean-detail-page.md)).

### `SmartSearch` integration

The `SmartSearch` component sits above the filter tags and provides an AI-powered natural-language search entry point. When a user submits a natural-language query (or an image), `searchStore.performSmartSearch()` calls the AI search API, which returns structured `SearchParams`. The store applies these parameters (overwriting the current filter state), triggers `performNewSearch()`, and stores the `smartSearchQuery` for display. If the AI service is rate-limited, the store falls back to an FTS query with `sortBy = "relevance"` and surfaces the rate-limit reset time. This makes the faceted filter system and the AI search two entry points into the same underlying query pipeline. See [guided-discovery.md](guided-discovery.md) for the broader discovery flow.

## Sort options

| Sort value | Label | SQL mapping | Notes |
|---|---|---|---|
| `date_added` | Freshness | `sb.date_added` | Default sort (newest first) |
| `relevance` | Relevance | `score DESC, name ASC, sb.id ASC` | Uses scoring mode; partitions into matching/similar |
| `roaster` | Roaster | `sb.roaster` | Alphabetical by roaster name |
| `price` | Price | `sb.price_usd / sb.weight` | Price per gram |
| `price_large` | Bulk price | `COALESCE(sb.lb_price_per_kg_usd, ...)` | Price per kg of largest bag |
| `name` | Name | `sb.name` | |
| `origin` | Origin | `sb.country` | |
| `region` | Region | (via origin fields) | |
| `elevation` | Elevation | `sb.elevation_min` | |
| `variety` | Variety | `sb.variety` | |
| `process` | Process | (via origin fields) | |
| `cupping_score` | Cupping Score | `sb.cupping_score` | |
| `weight` | Weight | `sb.weight` | |

Sort order cycles through `desc`, `asc`, and `random`. The `random` order uses `hash(concat(sort_field, sb.scraped_at, current_date()))` for a stable-but-shuffled daily order. All strict-mode sorts append `sb.id ASC` as a deterministic tiebreaker so paginated `LIMIT/OFFSET` queries return a stable order across pages.

## Currency conversion

Price filters and display respect the user's selected currency via `convert_to_currency`. The `searchStore.buildSearchParams()` appends `convert_to_currency: currencyState.selectedCurrency` to every API call. On the backend, the endpoint validates the currency code (must be a 3-letter ISO 4217 code) and, if non-USD, converts `min_price`/`max_price` from the target currency to USD using `convert_price()` before building the range filter. The main query's `SELECT` uses `_build_currency_select_sql()` to project the price in the requested currency and mark `price_converted = true`. See [price-transparency.md](../concepts/price-transparency.md) for the broader pricing model.

## Failure and edge-case handling

- **Invalid filter values (400)**: If the API returns a 400 (e.g. invalid query syntax), `+page.ts` catches the error and returns it as `searchError` data rather than throwing, so the page renders with an error message and the filter form remains usable. The user can correct the input and retry.
- **Network errors**: `performNewSearch()` catches errors and sets `error` in the store, clearing results. `loadMore()` logs the error but preserves existing results so the user doesn't lose their scroll position.
- **Duplicate IDs across pages**: Non-deterministic pagination on ties (before the `sb.id` tiebreaker was added) could return the same bean on multiple pages. The `loadMore()` dedup guard filters incoming beans by `id` against the existing set, preventing Svelte `{#each}` reconciliation `RangeError`s.
- **Empty filter state**: `clearFilters()` resets every field and triggers a new search. The `hasFiltersApplied` derived value in `+page.svelte` drives the conditional rendering of the "Clear Filters" button.
- **Roaster location defaults**: When the user clears location filters, `updateURL()` writes `apply_location_defaults=false` to prevent the server-side load from re-applying user defaults on the next navigation.
