---
type: "Reference"
title: "Frontend"
description: "SvelteKit 5 frontend: route structure, API client with smart search integration, tasting wizard, brew assistant, vault, local-first sync, authentication, SEO, and PWA support."
tags: ["frontend", "sveltekit", "api-client", "search", "sync", "pwa", "auth"]
verified:
  - by: openwiki/0.4.3
    at: 2026-08-29T13:59:13.975Z
sources:
  - id: openwiki-source-0bdf50a0b0b0618dd3a5abe8
    resource: repo://frontend/src/hooks.server.ts
  - id: openwiki-source-4735c40fd9ffe1e0754310f9
    resource: repo://frontend/src/lib/api.ts
  - id: openwiki-source-c7b4b3a4f26a7a2cd618e2d9
    resource: repo://frontend/src/lib/auth-client.ts
  - id: openwiki-source-24225342590a035226d3afa6
    resource: repo://frontend/src/lib/components/search/SearchFilters.svelte
  - id: openwiki-source-4f1dcbba82a22f2de93ef7d2
    resource: repo://frontend/src/lib/constants.ts
  - id: openwiki-source-34635a6d4b8510a5068d146c
    resource: repo://frontend/src/lib/db/updates.svelte.ts
  - id: openwiki-source-2c2bbcc69b284d37cd34fa13
    resource: repo://frontend/src/lib/server/auth.ts
  - id: openwiki-source-b9b678dc2f547df4edcc8159
    resource: repo://frontend/src/lib/stores/search.ts
  - id: openwiki-source-3898969b0e83860a4f243278
    resource: repo://frontend/src/lib/sync/customBeanSync.ts
  - id: openwiki-source-ca2e2e19e65624acfc12f078
    resource: repo://frontend/src/lib/sync/savedBeanSync.ts
  - id: openwiki-source-f735afd234bf9e1b884fd33a
    resource: repo://frontend/src/lib/sync/syncManager.svelte.ts
  - id: openwiki-source-bb04c0a0b633154d8d466183
    resource: repo://frontend/src/lib/sync/verifySync.ts
  - id: openwiki-source-e4b1a68e7f8622f9689cc98d
    resource: repo://frontend/src/routes/.well-known/http-message-signatures-directory/%2Bserver.ts
  - id: openwiki-source-7a334d3b594b4fd3d6f47b8b
    resource: repo://frontend/src/routes/(main)/%2Bpage.svelte
  - id: openwiki-source-b51e5ca2df09a80d0a0e26b1
    resource: repo://frontend/src/routes/(main)/origins/%5Bcountry_code%5D/%2Bpage.svelte
  - id: openwiki-source-e0be2b6e3635bb968ac620b2
    resource: repo://frontend/src/routes/(main)/profile/%2Bpage.svelte
  - id: openwiki-source-ea91b596889d1b7a5331eef0
    resource: repo://frontend/src/routes/(main)/roasters/%2Bpage.svelte
  - id: openwiki-source-3caf6a98926cd5705188c6a2
    resource: repo://frontend/src/routes/(main)/roasters/%5Broaster_name%5D/%2Bpage.svelte
  - id: openwiki-source-be5ca84f39efd71f618e9a90
    resource: repo://frontend/src/routes/(main)/search/%2Bpage.svelte
  - id: openwiki-source-b758e3b985bb52cc309a9668
    resource: repo://frontend/src/routes/(main)/vault/saved/%2Bpage.svelte
generated: { by: "openwiki/0.4.3", at: "2026-08-29T13:59:13.975Z" }
---

# Frontend

## Overview

The frontend is a SvelteKit 5 application (runes mode) using shadcn-svelte UI components, Tailwind CSS v4, TypeScript, and Bun as the package manager. It provides a modern, responsive interface for discovering and exploring coffee beans.

## Route Structure

```
frontend/src/routes/
├── (main)/                    # Primary layout group
│   ├── +page.svelte           # Home page (hero, search, featured roasters)
│   ├── search/                # Advanced search with faceted filters
│   ├── roasters/
│   │   ├── +page.svelte       # All roasters listing
│   │   └── [roaster_name]/    # Roaster profile + beans
│   │       └── [bean_name]/   # Bean detail page
│   ├── origins/               # Geographic origin browser
│   │   └── [country_code]/    # Country profile
│   │       └── [region_slug]/ # Region profile
│   ├── flavours/              # Tasting note / flavour explorer
│   ├── processes/             # Processing method pages
│   ├── varietals/             # Varietal pages
│   ├── roasted-in/            # Beans roasted-in a location
│   ├── brew-assistant/        # AI brew recipe generator (beta-gated)
│   ├── tasting/               # Tasting wizard + history
│   ├── vault/
│   │   ├── collection/        # User's bean collection
│   │   ├── saved/             # Saved beans
│   │   └── recently-viewed/   # Recently viewed beans
│   ├── profile/               # User profile + settings
│   ├── admin/                 # Admin dashboard
│   └── login/                 # Login entry
├── (no-layout)/               # Standalone pages (no main layout)
├── auth/                      # Authentication (magic-link email via better-auth)
├── og/                        # Open Graph image generation
├── sitemap.xml/               # Main sitemap
├── sitemap-origins.xml/       # Origins sitemap
├── sitemap-processes.xml/     # Processes sitemap
├── sitemap-varietals.xml/     # Varietals sitemap
└── sitemap-static.xml/        # Static pages sitemap
```

## Well-Known Routes

- `/.well-known/http-message-signatures-directory/` — Serves a JWKS-formatted Ed25519 public key with a signed HTTP response, enabling target servers to verify the scraper's Web Bot Auth identity. Requires `BOT_PRIVATE_KEY_PEM` and optionally `BOT_KEY_ID` / `BOT_PUBLIC_KEY_X` env vars. Returns `application/http-message-signatures-directory+json` with `Signature` and `Signature-Input` headers.

## API Client (`frontend/src/lib/api.ts`)

Central TypeScript API client that handles all backend communication. It defines the core domain types (`Bean`, `CoffeeBean`, `Roaster`, `RoasterStatistics`, `RoasterDetailResponse`) used across routes and components, and exposes typed fetch wrappers for the backend REST API. Modular remote APIs live under `frontend/src/lib/api/` (e.g. `custom_beans.remote.ts` for user-created beans, `profile.remote.ts` for profile, `roaster_suggestions.remote.ts` for community roaster suggestions).

### Smart Search Integration

The API client provides two methods for AI-powered natural language search:

- `smartSearchParameters(query)` — text-based search via `POST /api/v1/ai/search`
- `smartImageSearchParameters(imageFile)` — image-based search via `POST /api/v1/ai/imagesearch`

Both convert the `SmartSearchParameters` response (which includes `search_text`, `tasting_notes_search`, `roaster`, `roaster_location`, `origin`, `region`, `producer`, `farm`, `variety`, `process`, `roast_level`, `roast_profile`, price/elevation ranges, and boolean filters) into the `SearchParams` format used by the `GET /api/v1/search` endpoint. All fields are mapped, including `farm` and `producer` (wildcard-capable fields). A `429` response is detected and returned as an `error: "rate_limited"` result carrying `rateLimitResetAt` / `rateLimitLimit` so the UI can surface rate-limit state rather than a generic failure.

The search store (`frontend/src/lib/stores/search.ts`) consumes these results. `performSmartSearch()` applies the returned parameters to the store state (roaster, origin, region, producer, farm, roast level/profile, process, variety, price/weight/elevation ranges, decaf/single-origin/tasting-kit flags, sort) and then triggers `performNewSearch()`. On rate-limit it falls back to a plain full-text query with `sortBy: "relevance"`. The home page delegates its hero smart-search box and image search to `searchStore.performSmartSearch` / `performImageSearch`, threading the user's default roaster locations through.

## Key Features

### Home Page (`frontend/src/routes/(main)/+page.svelte`)

The home page renders a hero with `SmartSearch` (text + image), a `CoffeeJourney` guided-discovery section, and animated stats counters (beans, roasters, farms, flavours, roaster countries, origin countries) sourced from the server `dataPromise`. Smooth scrolling is provided by Lenis, with scroll-progress and section-visibility state driving parallax and reveal animations. This page — together with the CoffeeJourney component — implements the guided-discovery concept; see [guided-discovery.md](../design/guided-discovery.md).

### Search & Faceted Filters

The search page (`frontend/src/routes/(main)/search/+page.svelte`) initialises the search store from server-loaded data on both server and client, supports infinite scroll via `LoaderState`, and applies shared-image search results from form actions. The `SearchFilters` component (`frontend/src/lib/components/search/SearchFilters.svelte`) is a bindable, debounced filter panel exposing text and tasting-note queries; roaster and roaster-location multi-selects (the roaster list narrows to the selected location); origin, roast level, roast profile, process, variety, region, producer, and farm filters; price/weight/elevation (and large-bag weight) ranges; in-stock, tasting-kit, decaf, and single-origin toggles; and sort controls. For the faceted-filtering concept behind these controls, see [faceted-filtering.md](../design/faceted-filtering.md).

### Tasting Wizard (`frontend/src/lib/tasting/` + `components/tasting/TastingWizard.svelte`)
- Guided coffee tasting experience with drag-and-drop note ordering
- Bean search combobox for selecting the bean being tasted
- Add bean form for beans not in the database
- Save/unsave beans to vault from the wizard
- Tasting notes are categorised using the taxonomy described in [tasting-note-taxonomy.md](../concepts/tasting-note-taxonomy.md)

### Brew Assistant (`frontend/src/routes/(main)/brew-assistant/+page.svelte`)
- Beta-gated AI-powered recipe generator
- Sends bean attributes and user equipment to `POST /v1/brew-assistant/recipe`
- Returns personalised pour-over/espresso recipes

### Vault
- User's saved beans, collection, and recently-viewed beans
- Bean card actions: save/unsave, share to BeanConqueror
- Saved beans are synced via full reconciliation (see [sync system](sync-system.md))

### Sync System (`frontend/src/lib/sync/`)

The frontend uses a **local-first sync architecture**: Dexie (IndexedDB) stores all user data locally for offline use, with bidirectional sync to a remote Turso/libSQL database via Drizzle ORM and SvelteKit server endpoints.

**Four synced data types:**
- **Tasting sessions** — push/pull with `since` cursor, last-write-wins
- **Custom beans** — push/pull with `since` cursor, batch push (50/batch)
- **Saved beans** — push via individual save/unsave/notes commands + full reconciliation pull
- **Brew recipes** — push/pull with `since` cursor, only `isSaved` recipes are synced

**Key features:**
- Three sync modes: `normal` (incremental), `verify-then-fix` (count+digest check then targeted repair), `force-full` (re-fetch everything)
- SHA-256 digest-based consistency verification that catches content drift without downloading full payloads
- Offline-first: reads always come from Dexie; writes go to Dexie immediately with `syncedAt = null`; sync retries on next cycle
- Guest-to-user claiming: unowned local records are assigned to the logged-in user on first sync
- Reactive Svelte 5 runes trigger UI updates via `dbUpdateTrigger` counters

For full architecture details, protocol, schema evolution, conflict resolution, and change guidance, see **[sync-system.md](sync-system.md)**.

### State Management (`frontend/src/lib/stores/`)
- Svelte stores for theme, search state, user session, etc.
- `currency.svelte.ts` — Currency state with localStorage-cached rates (23h TTL matching server) for synchronous conversion on repeat visits; imports shared constants from `frontend/src/lib/constants.ts` (`CURRENCY_COOKIE_NAME`, `RATES_CACHE_KEY`, `RATES_TTL_MS`, `DEFAULT_CURRENCY`) so SSR and client agree on cookie/cache keys. The cookie name is deliberately centralised: if SSR and client ever disagree, `convert_to_currency` URL params diverge and defeat SvelteKit's load-fetch deduplication.
- `userSettings.svelte.ts` — User settings (e.g. `betaEnabled`) consumed by beta-gated routes and origin podcast sections.

### Authentication
- Magic-link email auth via `better-auth`
- `frontend/src/lib/auth-client.ts` — Auth client
- `frontend/src/routes/auth/` — Auth routes
- Server-side hooks in `hooks.server.ts` handle session middleware

### Profile & Beta Gating
- `frontend/src/routes/(main)/profile/+page.svelte` — User profile editor (name, newsletter subscription, beta access, beta interest, default roaster locations) backed by `profile.remote.ts`. Unsaved-change detection compares current values against a persisted baseline so reverting an edit clears the warning. Beta flags gate features such as the brew assistant and origin podcast insights.

### BeanConqueror Share
- `BeanConquerorShareButton.svelte` — Generates a share link that opens the BeanConqueror app with pre-filled bean data
- Uses protobuf-encoded, base64-chunked URL parameters

### Cloudflare Images
- `frontend/src/lib/utils/cfImage.ts` — Utility for generating Cloudflare Images CDN URLs for resized product images
- `ResponsiveImage.svelte` — Responsive image component using CF Images

### SEO
- Sitemap routes for origins, processes, varietals, and static pages
- `frontend/src/lib/seo.ts` — SEO metadata utilities (including `toAbsoluteUrl`)
- Open Graph image generation at `/og/` (including per-origin OG images via `/og/origin/<CODE>`)

### PWA
- `frontend/src/service-worker.ts` — Service worker for PWA support (also caches/resizes shared images client-side)
- `frontend/src/lib/pwa-install.svelte.ts` — PWA install prompt

## Route → Design Concept Cross-Reference

| Route / feature area | Design & UX concept |
| --- | --- |
| Home page + CoffeeJourney | [guided-discovery.md](../design/guided-discovery.md) |
| Search + `SearchFilters` | [faceted-filtering.md](../design/faceted-filtering.md) |
| `origins/[country_code]` routes | [origin-exploration.md](../design/origin-exploration.md) |
| `roasters/[roaster_name]/[bean_name]` bean detail | [bean-detail-page.md](../design/bean-detail-page.md) |
| Roasters listing + roaster uniqueness | [roaster-exploration.md](../design/roaster-exploration.md) |
| Stats / analytics insights | [analytics-insights.md](../design/analytics-insights.md) |

## Components (`frontend/src/lib/components/`)

Key components:
- `CoffeeBeanCard.svelte` — Bean card with image, name, roaster, tasting notes
- `bean/BeanCardActions.svelte` — Action buttons (save, share, etc.)
- `bean/BeanConquerorShareButton.svelte` — BeanConqueror share button
- `tasting/TastingWizard.svelte` — Full tasting wizard
- `tasting/AddBeanForm.svelte` — Add custom bean form
- `tasting/BeanSearchCombobox.svelte` — Bean search combobox
- `vault/SaveBeanButton.svelte` — Save/unsave bean to vault
- `FlavourProfileDonut.svelte` — 3D flavour visualisation (Threlte/Three.js), rendered on roaster profiles when flavour categories are present
- `RoastProfileBar.svelte` — Roast profile visualisation, rendered on the roaster page from `data.roast_distribution`; the page shows a flavour-profile-only fallback when roast data is insufficient for the chart
- `RoasterCard.svelte`, `RoasterStickerWall.svelte` — Roaster listing tiles and sticker wall
- `ElevationMountainChart.svelte`, `GeographyBreadcrumb.svelte`, `InsightCard.svelte`, `ExpertInsightsSection.svelte`, `UniversalOriginSearch.svelte` — Origin-exploration components
- `CurrencySelector.svelte` — Currency selector
- `ResponsiveImage.svelte` — Responsive CF Images component

### Roaster Uniqueness Rendering

The roaster profile page (`routes/(main)/roasters/[roaster_name]/+page.svelte`) renders a multi-dimensional uniqueness report from `data.uniqueness` (`top` insight + `by_dimension` map): a dimension-aware headline sentence plus secondary dimension chips. The `uniquenessSentence()` helper generates grammatically correct two-sentence statements per dimension — "sourcing skews" (origin), "tasting notes skew" (flavour), "processing skews" (process), "varietals skew" (varietal) — each citing this-roaster vs global percentage, lift, percentile, and sample size. Flavour/process labels are lowercased in the detail sentence; origin/varietal labels keep proper case. See the roaster-exploration concept ([roaster-exploration.md](../design/roaster-exploration.md)) and the backend algorithm in [roaster-uniqueness.md](../api/roaster-uniqueness.md).

## Server Hooks

- `hooks.server.ts` — Sentry initialisation, auth session middleware, request logging
- `hooks.client.ts` — Client-side Sentry, theme initialisation
- `instrumentation.server.ts` — Sentry server instrumentation

## Configuration

- `svelte.config.js` — SvelteKit configuration (adapter, preprocessing)
- `vite.config.ts` — Vite build configuration
- `package.json` — Dependencies (SvelteKit, shadcn-svelte, Tailwind, Threlte, better-auth, Dexie, Drizzle, etc.)
- `app.html` — HTML template
- `app.css` — Global styles (Tailwind)

## Related Pages

- [backend-api.md](../api/backend-api.md) — Backend REST API consumed by this client
- [tasting-note-taxonomy.md](../concepts/tasting-note-taxonomy.md) — Tasting note categorisation used by the wizard and flavour explorer
- [sync-system.md](sync-system.md) — Local-first sync architecture detail
- [email-notifications.md](email-notifications.md) — Email/notification flows
