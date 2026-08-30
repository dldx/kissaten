---
type: frontend-page-design
title: Roaster & Origin Exploration Flows
description: Design documentation for the roaster exploration flow — the roasters listing page with sticker wall, roaster detail page with uniqueness report and flavour distribution, the roaster-to-bean drill-down, and the roasted-in location exploration that groups roasters by where they roast.
tags: [roaster-exploration, roaster-detail, sticker-wall, uniqueness-report, roasted-in, location-exploration, svelte, frontend]
verified:
  - by: openwiki/0.4.3
    at: 2026-08-29T13:59:13.975Z
sources:
  - id: openwiki-source-4735c40fd9ffe1e0754310f9
    resource: repo://frontend/src/lib/api.ts
  - id: openwiki-source-f3f4df18c941b708126bc31c
    resource: repo://frontend/src/lib/components/FlavourProfileDonut.svelte
  - id: openwiki-source-3a0b7ba6e0a7047299e286ac
    resource: repo://frontend/src/lib/components/LocationLayout.svelte
  - id: openwiki-source-f81a7eec6bbc96ce4a55ae10
    resource: repo://frontend/src/lib/components/RoasterCard.svelte
  - id: openwiki-source-5983d587a7f0e66fddcdf60a
    resource: repo://frontend/src/lib/components/RoasterStickerWall.svelte
  - id: openwiki-source-d03eaff6ea63c671874f79ee
    resource: repo://frontend/src/routes/(main)/roasted-in/%2Bpage.ts
  - id: openwiki-source-3cc79cc9d9ce4ce856153442
    resource: repo://frontend/src/routes/(main)/roasted-in/%5Bregion_slug%5D/%5Bcountry_slug%5D/%2Bpage.ts
  - id: openwiki-source-857698b07f28c82ee554618e
    resource: repo://frontend/src/routes/(main)/roasted-in/%5Bslug%5D/%2Bpage.svelte
  - id: openwiki-source-78d5b64568394536fda02efc
    resource: repo://frontend/src/routes/(main)/roasted-in/%5Bslug%5D/%2Bpage.ts
  - id: openwiki-source-ea91b596889d1b7a5331eef0
    resource: repo://frontend/src/routes/(main)/roasters/%2Bpage.svelte
  - id: openwiki-source-a6fd2eb7d1d9359084620a0d
    resource: repo://frontend/src/routes/(main)/roasters/%2Bpage.ts
  - id: openwiki-source-3caf6a98926cd5705188c6a2
    resource: repo://frontend/src/routes/(main)/roasters/%5Broaster_name%5D/%2Bpage.svelte
  - id: openwiki-source-602a354b684105ac2f013990
    resource: repo://frontend/src/routes/(main)/roasters/%5Broaster_name%5D/%2Bpage.ts
  - id: openwiki-source-508b1dba22d03350c5ff5202
    resource: repo://frontend/src/routes/(main)/roasters/%5Broaster_name%5D/%5Bbean_name%5D/%2Bpage.ts
  - id: openwiki-source-9735fcc3e14d5d9974206d6d
    resource: repo://src/kissaten/api/main.py
  - id: openwiki-source-03850ddb7bf63bf806a747c4
    resource: repo://src/kissaten/schemas/geography_models.py
  - id: openwiki-source-2dc6f01310832dc3247ee1da
    resource: repo://src/kissaten/schemas/roaster_models.py
generated: { by: "openwiki/0.4.3", at: "2026-08-29T13:59:13.975Z" }
---

# Roaster & Origin Exploration Flows

The roaster exploration flow is the browse path that takes a reader from the catalogue of all roasters down to a single coffee bean. It spans three SvelteKit routes under `(main)/roasters` and a parallel `(main)/roasted-in` tree that groups the same roasters by the location in which they roast. Along the way it surfaces the [roaster uniqueness report](../api/roaster-uniqueness.md), a flavour-profile donut, and a D3-force-driven sticker wall that doubles as a visual discovery surface.

## Exploration flow

The canonical drill-down is three levels deep, with the roasted-in tree as a location-first alternative entry point.

<!-- openwiki: mermaid parse failed and this diagram was converted to a text fence so it does not break rendering. Fix the diagram source and restore the mermaid fence. Parser error: Heuristic: an unescaped angle bracket inside a label breaks rendering; rephrase the label. -->
```text
flowchart TD
    Listing["/roasters — all roasters listing<br/>search + Grid/Sticker toggle"] --> Detail["/roasters/{roaster_name}<br/>roaster detail"]
    Detail --> Bean["/roasters/{roaster_name}/{bean_name}<br/>bean detail page"]
    RoastedIn["/roasted-in/{slug}<br/>region or country"] --> Listing
    RoastedIn --> Detail
    Detail --> Search["/search?roaster=...<br/>explore beans facet"]
```

The flow above shows the roasters listing as the hub, the roaster detail page as the per-roaster profile, and the bean detail page ([bean-detail-page.md](bean-detail-page.md)) as the leaf. The roasted-in tree feeds into both the listing (via continent quick-links) and individual roaster detail pages (via the `RoasterCard` location link).

## Roasters listing page (`/roasters`)

Route: `frontend/src/routes/(main)/roasters/+page.svelte`, with data loaded by `+page.ts`.

### Data load

`+page.ts` calls `api.getRoasters(fetch)`, which hits `GET /v1/roasters`. The backend (`src/kissaten/api/main.py`, `get_roasters`) joins `roasters` to `coffee_beans` to compute `current_beans_count`, then decorates each roaster with hierarchical `location_codes`, `country_slug`, and `region_slug` resolved from the scraper registry via `get_hierarchical_location_codes`. The response is cached in a `SimpleMemoryCache`. Roaster suggestions (community-submitted roasters not yet scraped) are loaded server-side by the sibling `+page.server.ts` and passed through as `data.suggestions`, so the combobox does not need a client-side remote fetch.

### Page content

The listing page renders, top to bottom:

- A page header with continent quick-links (`/roasted-in/africa`, `/roasted-in/asia`, `/roasted-in/europe`, `/roasted-in/european-union`, `/roasted-in/north-america`, `/roasted-in/south-america`, `/roasted-in/oceania`) and a "Suggest a Roaster" button.
- A debounced search input (300 ms debounce) that filters roasters client-side by name or location.
- A **Grid / Stickers view toggle**. Grid renders `RoasterCard` components in a responsive grid; Stickers renders the `RoasterStickerWall`.
- A results summary ("N roasters" or "Showing X of N roasters").
- An empty state that offers to clear the search or suggest the typed query as a new roaster.

The "Suggest a Roaster" dialog uses a combobox that merges already-implemented roasters with community suggestions, deduplicates against both sets, and submits via `submitRoasterSuggestion`. On success it optimistically prepends the new suggestion and calls `invalidateAll()` to refetch. Upvoting a suggestion requires a session and redirects to `/login` when anonymous.

### RoasterCard

`frontend/src/lib/components/RoasterCard.svelte` is the grid tile. It shows the roaster's `logo_sticker.png` (from `/static/data/roasters/{slug}/logo_sticker.png`), name, location, a website link (UTM-tagged), a relative "last updated" timestamp derived from `last_scraped`, and an "Explore N Beans" button that deep-links into search (`/search?roaster={name}&apply_location_defaults=false`). The location text is itself a link to `/roasted-in/{region_slug}/{country_slug}` when both slugs are present, which is the bridge from a roaster tile into the roasted-in location tree.

### RoasterStickerWall

`frontend/src/lib/components/RoasterStickerWall.svelte` (~27 KB) is the visual discovery surface shown when the user toggles to "Stickers". It is a physics-based collage of roaster logo stickers rather than a grid.

- **Layout engine**: a D3 force simulation (`d3-force` plus `d3-force-boundary`) with `forceX`/`forceY` positioning, `forceManyBody` charge, and a `forceCollide` whose radius is `STICKER_SIZE / 2 + PADDING`. Stickers are rendered as absolutely-positioned divs translated by the simulated `x`/`y` and given a stable per-roaster rotation.
- **Search interaction**: when a debounced search query is active, matched stickers are pulled into a centered band (`forceX` spread, stronger `forceY`), non-matches are dimmed (opacity 0.1) and pushed down, and collision is temporarily disabled for matches so they can float through each other before re-settling after a 1 s timeout.
- **Position caching**: a stable cache key hashed from the sorted roaster IDs is stored in `localStorage`. On an exact width/height match with all positions known, the simulation snaps to cached positions and stops; on a resize it scales cached positions proportionally and re-runs with a lower alpha.
- **Hit testing**: a Delaunay triangulation (`delaunay.find`) maps mouse moves to the nearest sticker for hover; click pins a `selectedRoaster` whose tooltip stays open until dismissed or a window click clears it.
- **Tooltip actions**: the pinned tooltip offers "Explore N Beans" (deep-link to `/search?roaster=...&apply_location_defaults=false`) and, when present, a UTM-tagged "Visit Website" link. It does not link directly to the roaster detail page — discovery from the sticker wall funnels through search.
- **Decoration**: randomly placed coffee-ring texture PNGs are rendered as background SVG `<image>` elements, and each sticker has layered glossy specular highlight gradients masked to the logo shape.

The same `RoasterStickerWall` component is reused by `LocationLayout.svelte` on the roasted-in pages, so the sticker view is consistent across the roasters listing and every location page.

## Roaster detail page (`/roasters/{roaster_name}`)

Route: `frontend/src/routes/(main)/roasters/[roaster_name]/+page.svelte`, loaded by `+page.ts`.

### Data load

`+page.ts` reads `roaster_name` from params, resolves the user's selected currency from the parent layout, and calls `api.getRoasterDetail(slug, currency, fetch)`, which hits `GET /v1/roasters/{roaster_slug}` with an optional `convert_to_currency` query. The backend (`get_roaster_detail` in `main.py`) looks up the roaster by lowercased slug, resolves country/region slugs from the scraper registry, computes bean-level statistics (`total_beans`, `available_beans`, `avg_cupping_score`, `avg_price_usd`, distinct origin and varietal counts), deduplicates beans by `clean_url_slug`, and assembles the full `RoasterDetailResponse`.

The load function returns the roaster, the full detail payload (`statistics`, `top_origins`, `varietals`, `processing_methods`, `common_tasting_notes`, `flavour_categories`, `roast_distribution`, `uniqueness`), and a **deferred beans promise** — `beans` and `pagination` are produced by `api.search({ roaster: detail.name, page, per_page, sort_by, sort_order })` and consumed in the template via `{#await beans}`. Sort and page changes update the URL search params (`sort_by`, `sort_order`, `page`, `q`) with `replaceState` + `noScroll` so SvelteKit's load re-runs without scrolling. A 404 from the API (`"not found"` in the message) is converted to a SvelteKit `error(404)`.

### Response model

`RoasterDetailResponse` (`src/kissaten/schemas/roaster_models.py`) carries everything the page needs in one payload:

| Field | Type | Role |
|---|---|---|
| `statistics` | `RoasterStatistics` | `total_beans`, `available_beans`, `total_origins`, `total_varieties`, `avg_cupping_score`, `avg_price_usd` |
| `flavour_categories` | `List[FlavourCategoryCount]` | Primary tasting-note category distribution (count + percentage) fed to the donut |
| `roast_distribution` | `List[RoastLevelCount]` | Roast-level counts ordered Light → Dark, fed to the roast bar |
| `uniqueness` | `Optional[UniquenessReport]` | Multi-dimensional standout report (see below) |
| `top_origins`, `varietals`, `processing_methods`, `common_tasting_notes` | `List[TopOrigin/TopVariety/TopProcess/TopNote]` | Per-roaster origin/process/varietal/note distributions |
| `beans` | `List[APISearchResult]` | Full bean list (the page also re-fetches beans via search for pagination) |

### Rendered content

The page renders, in order:

1. **Breadcrumb** (Home / Roasters / {roaster name}) and a back button.
2. **Header card**: roaster logo (`/static/data/roasters/{slug}/logo_sticker.png`), name, location with an `iconify-icon` `circle-flags` flag derived from `location_codes[0]` (falling back to a `MapPin`), and a website globe link. SEO metadata includes a canonical URL, an OG image at `/og/roaster/{roaster_name}`, and Twitter card image.
3. **Awards & Recognition** — only when `roaster.awards` is a non-empty array or string; rendered as pill badges.
4. **About {roaster name}** — the `description` text, or a dashed placeholder when absent.
5. **"What Makes Them Unique"** — the uniqueness report headline (see [Uniqueness report rendering](#uniqueness-report-rendering)).
6. **Flavour Profile** and **Roast Profile** — a two-column grid when roast data is sufficient (`roast_distribution` total ≥ 10), otherwise the flavour donut alone. The donut is mounted after a `requestAnimationFrame` to avoid SSR/layout jump.
7. **Coffee Beans from {roaster name}** — a bean search input, `SortControls`, and a `{#await beans}` grid of `CoffeeBeanCard` with skeleton placeholders, followed by `PaginationControls` when `total_pages > 1`.

> **Note on loaded-but-unrendered data.** The load function returns `statistics` (bean count, avg cupping score, avg price, origin/varietal totals) and the `top_origins`, `varietals`, `processing_methods`, and `common_tasting_notes` distributions, but the current template does not render a numeric statistics panel or those distribution lists directly. The visible distribution visualisations are the flavour donut and the roast bar; the remaining aggregates are available on the data object for future use.

### Uniqueness report rendering

The uniqueness report is computed entirely in the backend by `_compute_uniqueness_report` (see [roaster-uniqueness.md](../api/roaster-uniqueness.md) for the full algorithm). It compares a roaster's category shares across four dimensions — **flavour**, **origin**, **process**, and **varietal** — against the global average across all roasters, and returns the single strongest standout as `top` plus per-dimension winners as `by_dimension` (excluding the top dimension).

The frontend renders only the `top` insight as a two-sentence "What Makes Them Unique" statement:

- **Headline**: `"{name}'s {noun} skew {display_label} — more so than {percentile}% of roasters."` where the noun and verb adapt per dimension (e.g. "tasting notes skew" for flavour, "sourcing skews" for origin, "processing skews" for process, "varietals skew" for varietal). The `display_label` is bolded.
- **Detail**: `"{this_roaster_pct}% of their {noun} are {label}, versus {global_pct}% on average across the catalogue ({lift} pts, based on {sample_size} {unit})."` The lift is shown with a leading `+` when positive.

The `uniquenessSentence()` helper produces the four label fragments per dimension, lowercasing flavour/process labels inside the detail sentence while keeping origin/varietal proper-case spelling. The report is gated behind `{#if uniquenessTop && uniquenessSentenceTop}`, so the section is omitted entirely when no dimension clears the backend thresholds (lift > 2 pts, percentile > 60%, min sample size, and a per-category floor of 10% or 3 items).

The page also prepares, but does **not** currently render, the secondary dimension chips: `uniquenessChips` is derived from `Object.values(data.uniqueness.by_dimension)`, a `dimensionIcon()` helper maps each dimension to a lucide icon (Sparkles/MapPin/Droplets/Leaf), and a `DIMENSION_NOUN` map is defined. These are infrastructure for surfacing the `by_dimension` insights as chips that would link to the relevant exploration page (the backend `link` field on each `UniquenessInsight` already provides paths like `/origins/et`, `/processes/{slug}`, `/varietals/{slug}`); the chip markup is not present in the current template, which surfaces only the single top headline.

### Drill-down to a bean

Each bean card in the grid links to `/roasters/{roaster_name}/{bean_name}`, handled by `frontend/src/routes/(main)/roasters/[roaster_name]/[bean_name]/+page.ts`. That load calls `api.getBeanBySlug(roaster_name, bean_name, fetch, currency)` against `GET /v1/beans/{roaster_slug}/{bean_slug}`, throwing a SvelteKit `error(404)` when the bean is not found and the roaster is not `custom`. The full bean page design is documented in [bean-detail-page.md](bean-detail-page.md). The `custom` roaster slug is reserved for user-created beans stored in the local Dexie vault and hydrated client-side.

## Roasted-in location exploration (`/roasted-in/{slug}`)

The roasted-in tree is a location-first alternative to the roasters listing. It groups roasters by **where they roast** (their registered country), not where beans are grown, and shares the same `RoasterCard` / `RoasterStickerWall` presentation via `LocationLayout.svelte`.

### Hierarchy

```
/roasted-in                     → 301 redirect to /roasters
/roasted-in/{slug}              → region (e.g. europe, asia) or country
/roasted-in/{region_slug}/{country_slug}  → country within a region
```

The `/roasted-in` index (`+page.ts`) throws a `redirect(301, '/roasters')`. A single slug resolves to either a region (codes `XE`, `EU`, `XA`, `XF`, `XN`, `XS`, `XO`) or a country, determined by `get_location_detail` on the backend. The two-segment route verifies the hierarchy: `+page.ts` fetches both the country and region via `api.getLocationDetail` and throws `error(400, 'Invalid location hierarchy')` if the country's `location_type` is not `country` or the region's is not `region`.

### Backend endpoints

- `GET /v1/roaster-locations` (`get_roaster_locations`) — returns all location codes from `roaster_location_codes` with hierarchical roaster counts. For each code it walks the scraper registry, expands each roaster's country to its hierarchical codes via `get_hierarchical_location_codes`, and counts any roaster whose expansion contains the code. Regional codes (`XE` Europe, `EU` European Union) carry an `included_countries` list. Results are sorted by roaster count descending. This powers the continent quick-links and location filters.
- `GET /v1/roasted-in/{slug}` (`get_location_detail`) — resolves the slug (via `normalize_region_name`) to a location code, filters roasters hierarchically, and returns a `LocationDetailResponse` with `statistics` (`available_beans`, `total_beans`, `roaster_count`, `city_count` for countries, `country_count` for regions), `top_roasters`, `top_cities`, `top_origins`, `varietals`, and (for regions) `countries`. Both endpoints are cached in `SimpleMemoryCache`.

### Page content

`LocationLayout.svelte` is the shared shell for both the single-slug and two-segment routes. It renders breadcrumbs, a title, two stat cards (total beans — which links to `/search?roaster_location={code}` — and roaster count), insight cards for Popular Origins and Top Varietals (built from `top_origins`/`varietals` with deep-links into search), a roaster search input, the same Grid/Stickers toggle, and the roaster list. The region page additionally renders a countries grid (via the `countriesSection` snippet in `[slug]/+page.svelte`) where each country card shows its flag, bean and roaster counts, and links to `/roasted-in/{region_slug}/{country_slug}`.

The roasted-in flow connects back to the roaster detail page through the `RoasterCard` location link and the bean counts that deep-link into search, and to the broader discovery graph via the origin/varietal insight cards. Aggregate insights computed across these locations feed the site-wide analytics described in [analytics-insights.md](analytics-insights.md).
