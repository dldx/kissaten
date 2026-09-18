---
type: "Plan"
title: "Offline-First PWA — 2026-09"
description: "Plan to make the Kissaten PWA render cached beans and stats fully offline: fix the home-page dataPromise hang (blocks online too), harden the service worker (split caches, navigation fallback, opaque image caching, SW updates), add a Dexie-backed catalogue/API cache, and add offline UX + a verification harness."
---

# Offline-First PWA Plan — 2026-09

## Background & diagnosis (verified with CDP on the deployed site)

Investigation on `https://kissaten.app` (Chromium via `--remote-debugging-port=9222`,
raw CDP; note: `Network.emulateNetworkConditions(offline)` does NOT block loopback/CF
routing in this browser, so `Network.setBlockedURLs(["https://kissaten.app/*"])` is
the correct offline simulation tool) produced two findings that shape this plan:

1. **The frontpage uses SvelteKit streamed promises by design — and that is the
   offline gap.** `(main)/+page.ts` (l.25–33) returns `{ dataPromise }` so the SSR
   HTML ships immediately (home node serialized as `null` in
   `node_ids: [0, 2, 11], data: [null, {layout data}, null]`) and the API data
   hydrates via a streamed chunk + `await data.dataPromise` in `+page.svelte`
   (l.152–190, stats counters; `beansCounted` starts at `0+` and animates up when
   `#stats-section` scrolls into view via `statsVisible`). Online this works —
   `/api/v1/stats` returns `total_beans: 13648` (curl, page fetch, and SW cache
   bodies all agree), and the stream resolves. **Offline it cannot work**: the
   streamed chunk is a network response; when it is absent the `dataPromise` never
   resolves, the counters stay at `0+` and the carousel renders nothing. That is
   precisely the "cached beans & stats MUST render offline" gap, not an online
   regression. (One honest caveat: in our CDP session the counters stayed `0+`
   even online — attributed to instrumented-scroll flakiness (`.animate-section`
   gating + DevTools visibility), not confirmed breakage; the claim "broken
   online" in a previous draft was too strong and is retracted.)
2. **Current offline behavior** (controlled test with `setBlockedURLs`):
   - Previously visited routes render fully: the SW caches SSR HTML documents
     which embed their data (network-first + `cache.put` on every 200).
   - What fails offline: unvisited bean images (`/static/data/roasters/<r>/<date>/...`),
     roaster logos (132/413 broken on a cached /roasters page), all dynamic
     client-side API interactions (new searches, filters, pagination), and
     `manifest.json` on reloads.
   - Offline fallback for an uncached resource is a bare `408 "Network error"` text
     response — no app-shell / offline page.

## Scope (decision)

We do NOT need every feature to work offline:

- **Search does not need to work offline.** New queries, filters, and AI/smart
  search are network-only; they must degrade to a clear "offline" state, not crash.
- **Cached beans and stats MUST render offline**: previously visited pages, bean
  detail for cached beans, cached search-result pages, and the home stats.
- Vault/tastings/brew-recipe history already work offline (Dexie + sync engine —
  see [sync-system](../frontend/sync-system.md)) and must keep working.

## Target architecture — three cache layers

| Layer | Owner | Contents | Strategy |
|---|---|---|---|
| App shell + pages | SW Cache Storage | build chunks, fonts, icons, manifest, visited route documents | Precache at install; network-first for pages, fallback to cached `/` (never 408) |
| API data | Dexie new `apiCache` table in `KissatenDB` | `/v1/*` GET JSON responses (currency-aware keys) | Cache-first + stale-while-revalidate, per-endpoint TTL |
| Images | SW Cache Storage | bean photos incl. cross-origin opaque, roaster logos, `/cdn-cgi/image/*` | Runtime-cached, capped with eviction |

Rationale: Dexie for structured data (queryable, survives SW updates, TTL metadata,
existing Dexie/sync infrastructure); SW for opaque bytes (pages, images).

## Phase 0 — P0 offline-gap fixes for the streamed pages (do first)

The frontpage is a **suspense/streaming** page: by design the API is fetched after
the shell ships. The offence comes from the SW trying to "help" (caching a partial
`null` document) plus no fallback when the streamed chunk cannot arrive. Fixes:

1. **Make the streamed page resilient offline** (`(main)/+page.ts`, `+page.svelte`):
   - Keep streaming for online (it exists so the page does not wait on the API —
     do not regress to awaited `load()` as the default).
   - Add an offline-aware fallback: `Promise.race` the `dataPromise` against a
     short timeout (e.g. 3s); on timeout, hydrate from the offline cache
     (Phase 2: Dexie `apiCache`/`catalogueBeans` snapshots) instead of staying at
     `0+`. Annotate with `stale: true` so the banner can say "cached data".
   - Acceptance: online unchanged (counters animate via the real stream); offline
     after warming, counters show the cached numbers (e.g. `13,648+` or the
     last-known values) not `0+`; no console errors.
2. **Review other streamed `dataPromise` pages** — bean detail showed a
   permanent "Loading..." shell in the same session; check whether
   `frontend/src/routes/(main)/roasters/[roaster_name]/[bean_name]/+page.ts`
   (`getBeanBySlug` at l.31) streams too and apply the same offline fallback.
3. Re-run the CDP harness (Phase 4) after changes to verify online parity and the
   offline state.
3.**Verification** of both fixes on the deployed site via CDP before Phase 1.

Delivery note: this doc plans the work; implementation happens in follow-up PRs.

## Phase 1 — Service worker hardening (`frontend/src/service-worker.ts`)

1. Split caches: `shell-${version}` (precache), `pages-${version}`,
   `images-${version}` (keep the share_target `SharedImagesDB` IndexedDB handler as
   is). `activate` deletes all caches except `shell-${version}`.
2. Navigation handling: network-first; on failure serve the cached exact URL, else
   the cached `/` document as app shell (or a minimal offline.html). Never return
   the bare 408 text response for navigations.
3. API GETs: stale-while-revalidate with TTL (search 1h, lists 24h) as a second
   layer under the Dexie cache (Phase 2). Cache-key includes full query string +
   `convert_to_currency` so currency variants are separate entries.
4. Images: also `cache.put` opaque cross-origin responses
   (`response.type === 'opaque'` — bean photos on roaster CDNs are no-cors, so the
   current `status === 200` guard skips them). Add eviction: use
   `navigator.storage.estimate()`; when usage > ~70% of quota, evict LRU entries
   (record `date` in a Cache-Control-like meta or store a manifest entry per image).
5. Updates: `skipWaiting()` + `clients.claim()` in `activate`, `postMessage` to
   clients; app listens and shows a "new version — reload" toast (SvelteKit
   `updated` from `$app/state` is already available and currently unused).
6. Precache budget: drop `static/data/optimized_origins.json` (4.3 MB, no
   references found in `frontend/src` — verify with `rg` across the repo before
   removing) from the `files` glob; keep fonts (they ARE in the prod precache and
   serve fine) and icons.

## Phase 2 — Dexie catalogue cache (the "cached beans & stats" data layer)

1. Schema: `KissatenDB` v102 in `frontend/src/lib/db/localdb.ts` (follow the
   existing version-chain pattern at l.204–217):
   - `apiCache`: `key` (url incl. query+currency), `json`, `savedAt`, `ttlClass`.
   - `catalogueBeans`: `bean_url_path` → full `CoffeeBean` snapshot (detail-page
     offline fallback; can be fed from search results and bean-page loads).
2. New wrapper `frontend/src/lib/offline/apiCache.ts` wired into `KissatenAPI`
   (`frontend/src/lib/api.ts`, class at l.664):
   - Cache-first: return Dexie copy when fresh; background-refresh when online;
     serve stale when offline (never throw).
   - On network failure throw a typed `OfflineError` carrying the stale payload so
     load functions can render cached data instead of `error(500)`.
   - TTL policy: 24h for `countries/roasters/roaster-locations/processes/
     varietals/tasting-note-categories/currencies`, 1h for `search` and `stats`.
3. Degate the root layout (`frontend/src/routes/(main)/+layout.ts` l.19–23):
   serve `originOptions` / `allRoasters` / `roasterLocationOptions` instantly from
   Dexie, refresh in background. This currently gates every route.
4. Resilient load functions: sweep the pages from the earlier gap analysis
   (`roasters`, `roasters/[roaster_name]`,
   `roasters/[roaster_name]/[bean_name]`, `origins/*`, `processes/*`,
   `varietals/*`, `flavours`, `roasted-in/*`): on `OfflineError` return cached data
   + `stale: true` and render a subtle "offline data" badge; only genuinely unknown
   resources 404.
5. Bean detail fallback: offline → hydrate from `catalogueBeans` /
   `recentlyViewed` (already stores full bean snapshots via `trackBeanView` l.239).
6. Client-side navigation offline: SvelteKit's router errors when the route's
   `__data.json` fetch fails. Options (validate with a spike): (a) SW serves a
   synthetic `{"type":"data","nodes":[null,...]}` so the client router proceeds and
   client-side load functions run against the Dexie cache; or (b) `ssr=false` +
   client-only loads for the main catalogue routes. Prefer (a); (b) is the fallback.

## Phase 3 — Offline UX & interactions

1. Offline banner in `(main)/+layout.svelte` driven by `navigator.onLine` +
   `offline`/`online` events (mirrors the sync gating already at l.42–89):
   "You're offline — showing cached data".
2. Feedback outbox: queue `POST /api/v1/ai/feedback` (currently dropped offline)
   in a Dexie `outbox` table; flush on the `online` event like the sync engine.
3. Search UI offline states: infinite-scroll `loadMore` disabled with an explicit
   message; smart search (AI/image) shown as "requires connection". No unhandled
   promise rejections.
4. Image placeholders: inline SVG fallback for un-cached roaster logos and bean
   images (CoffeeBeanImage.svelte already has a fallback path at l.49–53 — extend
   to offline).

## Phase 4 — Verification harness (repeatable)

1. `scripts/offline-test.mjs` codifying the CDP methodology that worked:
   - Connect via browser-level CDP (`Target.attachToTarget`, flatten); Playwright
     `connectOverCDP` handshake fails on this browser, raw CDP is reliable.
   - **Use `Network.setBlockedURLs`** per origin under test — never
     `emulateNetworkConditions` (loopback/CF still resolves).
   - Scenarios (each: warm online → block → reload → assert):
     - `/` renders real stats (not `0+`) and cached carousel; no console errors.
     - `/search` renders the cached result set ("Showing N of M beans").
     - `/roasters` renders; allowlist for broken logos is empty (or tiny).
     - Bean detail for a visited bean renders fully with image.
     - `/varietals` navigation offline → graceful offline state (no error page).
     - Vault pages (saved/recently-viewed/tastings) fully functional offline.
   - Report: per-route pass/fail, failed-request URL list, console errors.
2. Run manually before any offline-related promotion; later optional GitHub
   Actions job.

## Risks & open questions

- Synthetic `__data.json` (Phase 2.6) is the hackiest piece — spike it early.
- Cache quota: ~14k beans' images exceed quota; eviction must be aggressive
  (LRU, cap per-roaster).
- Staleness: offline data is stale by definition; the banner + `stale` flag are
  the honest UX. Currency switching offline serves the last-fetched currency
  variant (keyed per `convert_to_currency`).
- `optimized_origins.json` removal: confirm zero references repo-wide before
  dropping (it is precached today, 4.3 MB).
- SW update UX: without `skipWaiting`, new versions never take control until all
  tabs close — Phase 1.5 fixes this; verify no user-data loss on forced reload
  (Dexie data is version-agnostic).