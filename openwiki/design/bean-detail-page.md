---
type: frontend-page-design
title: Bean Detail Page Information Architecture
description: Design documentation for the bean detail page — its information hierarchy, the slug-based load flow, tasting notes and flavour visualizations, origin traceability, roast profile, cupping score, multi-bag price options, recommendation engine, and BeanConqueror share integration.
tags: [bean-detail-page, information-architecture, flavour-profile, recommendations, beanconqueror, svelte, frontend]
verified:
  - by: openwiki/0.4.3
    at: 2026-08-29T13:59:13.975Z
sources:
  - id: openwiki-source-4735c40fd9ffe1e0754310f9
    resource: repo://frontend/src/lib/api.ts
  - id: openwiki-source-ac18dbcbd927ce055f844a29
    resource: repo://frontend/src/lib/components/bean/BeanActionButton.svelte
  - id: openwiki-source-106e56a47e07685a698d57c5
    resource: repo://frontend/src/lib/components/bean/BeanConquerorShareButton.svelte
  - id: openwiki-source-c2e6f7c9305ec627cde4dbb4
    resource: repo://frontend/src/lib/components/CoffeeBeanCard.svelte
  - id: openwiki-source-f3f4df18c941b708126bc31c
    resource: repo://frontend/src/lib/components/FlavourProfileDonut.svelte
  - id: openwiki-source-dd888436a83fc9b7a148805b
    resource: repo://frontend/src/lib/components/RecommendationTabs.svelte
  - id: openwiki-source-672470a76e59ca3e2d2c64ec
    resource: repo://frontend/src/lib/components/RoastProfileBar.svelte
  - id: openwiki-source-f13ac1e1991aaa132ea7b161
    resource: repo://frontend/src/lib/components/SunburstChart.svelte
  - id: openwiki-source-dde88107844b0e12342ff08a
    resource: repo://frontend/src/lib/components/tasting/BeanTastingsCard.svelte
  - id: openwiki-source-14d82312bef47575e0aec2f4
    resource: repo://frontend/src/lib/utils.ts
  - id: openwiki-source-e82cbceb50788e7b9c868909
    resource: repo://frontend/src/routes/(main)/flavours/%2Bpage.svelte
  - id: openwiki-source-3caf6a98926cd5705188c6a2
    resource: repo://frontend/src/routes/(main)/roasters/%5Broaster_name%5D/%2Bpage.svelte
  - id: openwiki-source-284c300cf056039f15924d69
    resource: repo://frontend/src/routes/(main)/roasters/%5Broaster_name%5D/%5Bbean_name%5D/%2Bpage.svelte
  - id: openwiki-source-508b1dba22d03350c5ff5202
    resource: repo://frontend/src/routes/(main)/roasters/%5Broaster_name%5D/%5Bbean_name%5D/%2Bpage.ts
  - id: openwiki-source-f5f31640f5410e2338a4b6da
    resource: repo://src/kissaten/api/beanconqueror_share.py
  - id: openwiki-source-9735fcc3e14d5d9974206d6d
    resource: repo://src/kissaten/api/main.py
  - id: openwiki-source-0d95f608f6d7d340f981a2cc
    resource: repo://src/kissaten/schemas/api_models.py
generated: { by: "openwiki/0.4.3", at: "2026-08-29T13:59:13.975Z" }
---

# Bean Detail Page Information Architecture

The bean detail page is the deepest leaf in Kissaten's browse hierarchy: a single coffee bean presented with its full provenance, tasting profile, pricing, and discovery affordances. It lives at the SvelteKit route `/roasters/[roaster_name]/[bean_name]` and renders from a slug-resolved `APICoffeeBean`. Users arrive here from [faceted-filtering.md](faceted-filtering.md) search results, [roaster-exploration.md](roaster-exploration.md) roaster pages, origin/varietal/process detail pages, recommendation cards, and the local vault.

## Route and data load

The route is a standard SvelteKit page with a `+page.ts` load function and a `+page.svelte` component.

`+page.ts` extracts `roaster_name` and `bean_name` from the URL params (already in slug form) and calls `api.getBeanBySlug(roaster_name, bean_name, fetch, currencyState.selectedCurrency)`, which hits `GET /v1/beans/{roaster_slug}/{bean_slug}` with an optional `convert_to_currency` query parameter. The backend resolves the bean by matching `bean_url_path = '/{roaster_slug}/{bean_slug}'`, decorates tasting notes with their primary category inline, fetches all origins, and assembles `price_options`. If the bean is not found and the roaster is not `custom`, the load throws a SvelteKit `error(404)`. A `FeedbackContext` is built from the loaded bean so the inline feedback trigger can report field-level issues.

### Custom bean hydration

When `roaster_name === 'custom'`, the bean is a user-created entry stored in the local Dexie vault, not the server `coffee_beans` table. The load function returns `bean: null, isCustom: true` synchronously (Dexie cannot be touched during SSR), and `+page.svelte` hydrates from `db.customBeans` in a client-side `$effect`. If the custom bean was deleted or lives on another device, the page flips `notFound` and shows a "Custom Bean Not Found" panel instead of an infinite spinner.

## Information hierarchy

The page uses a three-column responsive grid (`lg:grid-cols-4`): a sticky image column, a main content column, and a sidebar. The hierarchy below is the order a reader encounters.

<!-- openwiki: mermaid parse failed and this diagram was converted to a text fence so it does not break rendering. Fix the diagram source and restore the mermaid fence. Parser error: Heuristic: an unescaped angle bracket inside a label breaks rendering; rephrase the label. -->
```text
flowchart TD
    A[Breadcrumb: Home / Search / Roasters / Roaster / Bean] --> B[Sticky bean image<br/>click → expand dialog]
    A --> C[Main content column]
    A --> D[Sidebar]

    C --> C1[Bean name + roaster + save button]
    C1 --> C2[Attribute chips: countries, varieties, processes,<br/>roast level, roast profile, decaf, blend, tasting kit, cupping score]
    C2 --> C3[My Notes editor — if saved to vault]
    C3 --> C4[BeanTastingsCard: roaster tasting notes + local tasting history]
    C4 --> C5[Description card — markdown, sanitized]
    C5 --> C6[Origin Details card: per-origin country, region, farm,<br/>producer, elevation, coordinates, process, variety, harvest date]

    D --> D1[Purchase / Coffee Info card:<br/>price + weight, price options popover, stock status,<br/>roaster site link, cupping score, green price, date added]
    D1 --> D2[RecommendationTabs — discovery engine]
```

### Bean name, roaster, and image

The header renders the bean `name` as an `<h1>` with a `view-transition-name: bean-title`, the roaster name linked back to a `?roaster=` filtered search, and the roaster's location country. A `SaveBeanButton` lets the user save the bean to their vault. The sticky image column shows a `CoffeeBeanImage` (responsive, Cloudflare-backed) that opens a full-size expansion dialog on click; the dialog falls back to the roaster's logo sticker when the product image is missing.

### Attribute chips

A flex-wrapped row of colour-coded pill links, each deep-linking into a filtered search:

- **Countries** — one chip per unique origin country, with a `circle-flags` iconify flag, linking to `/origins/{country}`.
- **Varieties** — deduplicated `variety_canonical` values from origins, linked to `/varietals/{normalized}`.
- **Processes** — deduplicated per-origin processes, linked to `/processes/{normalized}`.
- **Roast level** — `bean.roast_level` rendered as "{level} roast", linked to `?roast_level=`.
- **Roast profile** — `bean.roast_profile` (with "Both" displayed as "Filter & Espresso"), linked to `?roast_profile=`.
- **Decaf** / **Blend** / **Tasting kit** — boolean attribute badges linking to their respective `?is_decaf=` / `?is_single_origin=false` / `?is_tasting_kit=true` searches.
- **Cupping score** — shown as "{score}/100" when `cupping_score > 0`.

These chips are the page's primary navigation back into [faceted-filtering.md](faceted-filtering.md), and each attribute maps to a domain concept: roast → [roast-levels-profiles.md](../concepts/roast-levels-profiles.md), score → [cupping-scores.md](../concepts/cupping-scores.md).

### Tasting notes display

Roaster-supplied tasting notes render inside `BeanTastingsCard` as colour-coded pill links. Each note is coloured by its flavour category via `getFlavourCategoryColors` — the `primary_category` from the API decoration is preferred, falling back to `getCategoryForNote` from the tasting conversation module when no category was assigned. Clicking a note searches for other beans sharing it (`/search?tasting_notes_query="{note}"`). Notes preserve the roaster's original ordering (first-seen order from the normalized array), which encodes intended prominence — see [tasting-note-taxonomy.md](../concepts/tasting-note-taxonomy.md).

When the bean is saved and the user has beta features enabled, the card also shows the user's local tasting sessions (from Dexie) and offers a "Start Guided Tasting" / "New Guided Tasting" button linking to `/tasting?bean=`.

## Flavour profile visualizations

The bean detail page itself surfaces tasting notes as coloured pills, while the two dedicated chart components render richer flavour distributions on adjacent pages. Both share the canonical `FLAVOUR_CATEGORY_ORDER` and `getFlavourCategoryHexColor` palette from `frontend/src/lib/utils.ts`, so colours are consistent wherever flavour categories appear.

### SunburstChart

`SunburstChart.svelte` is an interactive, zoomable D3 partition (sunburst) flavour wheel. It consumes a `SunburstData` hierarchy — the three-tier tasting note taxonomy (primary → secondary → tertiary category) described in [tasting-note-taxonomy.md](../concepts/tasting-note-taxonomy.md). It is mounted on the `/flavours` page, where it visualises the global or filtered tasting-note universe.

Key behaviours:

- **Zoom on click** — clicking a parent arc zooms the chart into that subtree; the radius mapping switches to non-linear stepped weights at zoom depth ≥ 2 to give outer rings more label room.
- **Tasting-note click** — leaf nodes invoke `onTastingNoteClick`, adding the note to the user's search filter (desktop only; mobile shows a tooltip instead to avoid accidental filtering).
- **Pinch-to-zoom and pan** — on mobile (`< 768px`), the chart supports two-finger pinch zoom (0.5×–3×), single-finger drag panning, and double-tap to reset.
- **Label truncation** — arc labels are truncated with an ellipsis based on available arc length and font size, so small arcs don't overflow.
- **Flavour images** — when the `flavourImagesEnabled` setting is on, hovering a flavour fetches a representative image via `fetchAndSetFlavourImage`.

### FlavourProfileDonut

`FlavourProfileDonut.svelte` is a simpler category-distribution donut built on `layerchart`. It takes an array of `{ primary_category, count, percentage }` and renders a pie/donut with callout labels. It is mounted on the roaster page, where the `/v1/roasters/{slug}` endpoint returns a `flavour_categories` aggregate (primary-category counts across all of the roaster's beans, excluding non-flavour categories like Taste Basics, Mouthfeel, and Amplitude). Slices are sorted by `FLAVOUR_CATEGORY_ORDER`; labels for slices below 2% are hidden until hovered, and hovering a slice dims the others to avoid callout overlap. The donut centre shows the total note count.

### RoastProfileBar

`RoastProfileBar.svelte` renders a stacked horizontal bar showing the roast-level distribution across a roaster's catalogue (the five canonical buckets Light → Dark, with spelling variants normalised). It is mounted on the roaster page from the `roast_distribution` aggregate. Each segment links to a `?roast_level=` filtered search; narrow segments (< 5%) reveal their label only on hover via an above-bar callout with a leader line. The dominant roast (> 50% of beans) is highlighted. This gives the roaster page a roast overview complementary to the per-bean roast level shown on the detail page — see [roast-levels-profiles.md](../concepts/roast-levels-profiles.md).

## Origin details card

The Origin card iterates `bean.origins`, rendering one block per origin (labelled "Origin 1", "Origin 2"… for blends). Each origin exposes the full traceability hierarchy documented in [origin-geography.md](../concepts/origin-geography.md):

- **Country** (with flag and full name) → links to `/origins/{country}`
- **Region** → links to `/origins/{country}/{region_slug}` when a canonical region is available
- **Producer** and **Farm** → farm links to `/origins/{country}/{region}/{farm_slug}` when canonical names exist
- **Elevation** — `elevation_min`–`elevation_max` metres (single value when min == max)
- **Coordinates** — `latitude`/`longitude` to 4 decimal places
- **Process** → links to `/processes/{normalized}`
- **Variety** — renders `variety_canonical` as comma-separated links to `/varietals/{normalized}`
- **Harvest date** — formatted as month + year

The card footer states whether the bean is Single Origin or a Blend.

## Price options and purchase sidebar

The sidebar "Purchase" card (titled "Coffee Info" for custom beans) is the transactional surface.

### Price and weight

When `bean.price_options` has more than one entry (`hasVariants`), the price/weight summary becomes a popover trigger. The popover lists every bag size from `price_options` (ordered by weight ascending, as returned by the backend), showing each option's weight, price (in the bean's or converted currency), and a computed **price-per-kg** (`option.price / option.weight * 1000`). The current bag (matching `bean.weight`) is highlighted. When there is only one option, price and weight render inline.

### Largest-bag normalization

For search and comparison, the backend's `largest_bag` CTE selects, per bean, the price option with the greatest weight (and highest price as a tiebreaker) that has a non-null `price_per_kg_usd`. This normalizes multi-bag beans to a single comparable price-per-kg figure, surfaced as `price_large_weight`, `price_large_price`, and `price_large_price_per_kg_usd` on `APISearchResult`. The `CoffeeBeanCard` component can render this bulk price via a `useBulkPrice` prop, so card grids can show the largest-bag price for per-kg comparison. On the detail page, all bag sizes are shown explicitly in the popover instead. See [price-transparency.md](../concepts/price-transparency.md) for the distinction between retail pricing and green-coffee transparency fields.

### Stock status and provenance

- **In-stock status** — `bean.in_stock` renders as "✅ In stock" / "❌ Out of stock", with a relative "checked {duration} ago" timestamp derived from `scraped_at`.
- **Roaster site link** — `BeanActionButton` opens the roaster's product `bean.url` (with UTM referral parameters) in a new tab.
- **Cupping score** — repeated in the sidebar detail list as "{score}/100" when present.
- **Green price** — `price_paid_for_green_coffee` per kg, in its recorded currency, when the roaster published it.
- **First spotted** — relative time since `date_added`.

A disclaimer notes that prices and stock may not always be accurate, and a `FeedbackInlineTrigger` lets users report stale data.

## Recommendation engine

The sidebar mounts `RecommendationTabs`, a "Discovery Engine" card that fetches similar beans and lets the user switch between weighted recommendation profiles.

### Profiles

`RecommendationTabs` defines eight profiles, each a set of similarity weights sent to the backend:

| Profile | Focus | Key weight |
|---|---|---|
| Balanced | Overall character, roast, origin | tasting_notes 3.0, roast_level 1.0, origin 1.0 |
| Add/Remove Caffeine | Decaf swap | variety 5.0, tasting_notes 3.0; filters `is_decaf` to the opposite |
| Flavour | Matching specific tasting notes | tasting_notes 10.0, different_roaster 2.0 |
| Process | Similar processing methods | process 8.0 |
| Varietal | Same coffee varieties | variety 10.0 |
| Origin | Same regions/altitudes | origin 10.0 |
| Roast | Matching roast profile/colour | roast_level 8.0 |
| Roaster | Other beans from same roaster | roaster 100.0, different_roaster 0.0 |

### Endpoint and flow

The component calls `api.getDiscoveryRecommendations(bean, profile.weights, currency, 4, fetch, isDecafSwap, decafOnly)`, which resolves the bean's URL path into roaster/bean slugs and hits:

```
GET /v1/beans/{roaster_slug}/{bean_slug}/recommendations
```

The backend (`get_bean_recommendations_by_slug`) resolves the target bean, builds a `FilterParams` from its tasting notes (joined as a boolean OR query, with multi-word notes quoted), roaster, origin countries, roast level, processes, and varieties, then runs the shared scoring engine (`build_coffee_bean_filters` with `use_scoring=True`) over the deduplicated `coffee_beans` table. A `different_roaster_boost` adds points for beans from other roasters to encourage discovery. Results exclude the source bean (`cb.id != ?`) and only consider in-stock beans; they are returned as `APISearchResult` with a `similarity_score` and currency-converted prices. The frontend re-fetches whenever the bean, selected currency, or active profile changes, and renders up to four recommendation cards with their common tasting notes highlighted.

## BeanConqueror share integration

The page offers a "Save to BeanConqueror" action that generates a deep link importing the bean into the BeanConqueror mobile app. The action lives in `BeanActionButton` (for scraped beans, behind a dropdown alongside "View roaster page") and in `BeanConquerorShareButton` (for custom beans, a standalone button). It is gated on the user being signed in **and** the bean being saved to their vault.

### Wire format

The backend `beanconqueror_share.py` encodes the bean as a proto3 `BeanProto` message (generated from BeanConqueror's `bean.proto`), base64-encodes it, and chunks the result into 400-character `shareUserBeanN` URL parameters under `https://beanconqueror.com/?…`. The base64 is percent-encoded (safe="") because `+`, `/`, and `=` are unsafe in URL query strings. The trailing `/` before `?` is required — without it the OS universal-link routing opens the website instead of the app.

### Field mapping

The encoder maps kissaten fields onto the BeanConqueror proto:

- `name`, `roaster`, `url` → direct fields; `note` carries a back-reference to the Kissaten bean page.
- `tasting_notes` → comma-joined `aromatics` string.
- `weight` → grams (from `bean.weight` or the first price option with a weight).
- `price` → `cost` as a whole-unit integer in the target currency (the proto's `cost` is `uint64`, so sub-unit precision is truncated, matching the official app).
- `cupping_score` → `cupping_points` string.
- `is_decaf` → `decaffeinated` boolean.
- `roast_level` → `Roast` enum (six-bucket kissaten mapping to BeanConqueror's named roasts).
- `is_single_origin` → `beanMix` (SINGLE_ORIGIN / BLEND).
- `roast_profile` → `bean_roasting_type` (Filter/Espresso/Omni/Both).
- `origins[]` → repeated `bean_information` (country full name, region, farm, farmer/producer, elevation string, variety, processing, harvest time).

The encoder explicitly sets user-private fields (`favourite`, `rating`, `shared`, `finished`) to defaults and marks empty sub-messages (`config`, `bean_roast_information`, `cupping`, `cupped_flavor`) as present via `SetInParent`, so the BeanConqueror decoder sees defined values rather than `undefined` (which would break import).

### Endpoints

Two endpoints serve this:

- `GET /v1/beans/{roaster_slug}/{bean_slug}/beanconquerer-link` — resolves the bean server-side, embeds a `https://kissaten.app/roasters/{slug}/{slug}` back-reference, and returns `{ share_url }`. Accepts `convert_to_currency` to denominate the embedded price.
- `POST /v1/custom-beans/beanconquerer-link` — accepts the full custom bean body (stripped of `image_data`/`raw_data` via `stripBeanForShare`), backfills `country_full_name` from the `country_codes` table, overrides the proto `url` to point at the Kissaten custom-bean page, and reuses `build_share_link`.

Both are unauthenticated; the frontend gates the UI on sign-in and vault membership. The share dialog re-fetches the link when the selected currency changes while open, keeping the embedded price in sync, and renders a QR code for mobile scanning.

## SEO and structured data

The page emits a `<svelte:head>` block with a canonical URL, Open Graph product metadata (including a dynamically generated `/og/bean/{roaster}/{bean}` image at 1200×630), `product:price:amount` / `product:price:currency` tags, and a JSON-LD `Product` schema with an `Offer` (availability set from `in_stock`) — enabling rich product snippets and correct link previews when the detail URL is shared.

## Vault and tasting integration

The page is local-first for personal data: saved-bean status, custom-bean membership, user notes, and tasting history all read from the Dexie `savedBeans` / `customBeans` stores and re-evaluate on a `dbUpdateTrigger`. A bean view is tracked via `trackBeanView` on mount. The "My Notes" editor (`BeanNotesEditor`) and the tasting-session list (`BeanTastingsCard`) appear only when the bean is saved, keeping the public detail page lightweight while rewarding signed-in users who curate a collection.
