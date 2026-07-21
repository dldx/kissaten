---
type: "Reference"
title: "Local-First Sync System"
description: "Dexie (IndexedDB) to Turso/libSQL bidirectional sync architecture: four synced data types, three sync modes, SHA-256 digest verification, conflict resolution, and guest-to-user claiming."
---

# Local-First Sync System

## Overview

Kissaten uses a **local-first sync architecture** that lets users interact with their data (tasting sessions, saved beans, custom beans, brew recipes) offline and synchronizes changes bidirectionally with a remote SQLite database when online. The local store is **Dexie (IndexedDB)**; the remote store is **Turso/libSQL via Drizzle ORM**, exposed through SvelteKit server-side `command`/`query` endpoints.

## Architecture

```
┌───────────────────────┐         ┌──────────────────────────────┐
│   Browser (Client)    │         │      SvelteKit Server         │
│                       │         │                              │
│  Dexie / IndexedDB    │◄──────►│  Drizzle ORM → Turso/libSQL  │
│  (KissatenDB)         │  HTTP   │  (SQLite)                    │
│                       │  push/  │                              │
│  5 tables:            │  pull   │  4 sync tables + auth tables  │
│  - recentlyViewed     │         │                              │
│  - tastings           │         └──────────────────────────────┘
│  - customBeans        │
│  - savedBeans         │
│  - brewRecipes        │
└───────────────────────┘
```

### Key source files

| File | Purpose |
|---|---|
| `frontend/src/lib/db/localdb.ts` | Dexie database definition, schema versions, local CRUD helpers, owner-claiming logic |
| `frontend/src/lib/sync/syncManager.svelte.ts` | Orchestrates global sync across all four tables; exposes `syncState` and `runGlobalSync()` |
| `frontend/src/lib/sync/tastingSync.ts` | Push/pull sync for tasting sessions |
| `frontend/src/lib/sync/customBeanSync.ts` | Push/pull sync for custom beans |
| `frontend/src/lib/sync/savedBeanSync.ts` | Push + full reconciliation for saved beans |
| `frontend/src/lib/sync/brewRecipeSync.ts` | Push/pull sync for brew recipes |
| `frontend/src/lib/sync/verifySync.ts` | Count + SHA-256 digest consistency check across all tables |
| `frontend/src/lib/server/database/schema.ts` | Drizzle schema for server-side SQLite tables |
| `frontend/src/lib/server/database/index.ts` | Drizzle/Turso client initialization |
| `frontend/src/lib/api/tastings.remote.ts` | Server-side push/pull/count/digest endpoints for tastings |
| `frontend/src/lib/api/custom_beans.remote.ts` | Server-side push/pull/count/digest endpoints for custom beans |
| `frontend/src/lib/api/vault.remote.ts` | Server-side save/unsave/list/count/digest endpoints for saved beans |
| `frontend/src/lib/api/brew.remote.ts` | Server-side push/pull/count/digest endpoints for brew recipes |
| `frontend/src/lib/db/updates.svelte.ts` | Reactive trigger system (`dbUpdateTrigger`) for Svelte 5 runes |

## Local Database (Dexie/IndexedDB)

### Schema Evolution

The Dexie database (`KissatenDB`) has evolved through 11 schema versions:

| Version | Change |
|---|---|
| 1 | `recentlyViewed` table (bean view tracking) |
| 2–3 | `tastings` table added with `date`, then `name` index |
| 4–5 | `beanUrlPath` index added to `tastings` |
| 6 | **Sync fields added** to `tastings`: `syncId`, `updatedAt`, `deletedAt`, `syncedAt`; upgrade backfills existing records with UUIDs and timestamps |
| 7 | `ownerId` field added to `tastings` for multi-user support; upgrade backfills as `null` (guest) |
| 8 | `customBeans` table added with sync fields from the start |
| 9 | `savedBeans` table added |
| 100 | **Force schema reset** — same stores as v9; used to clear desynchronized high-version browser states |
| 101 | `brewRecipes` table added with `isSaved`, `lastUsedAt` indexes |

### Tables

#### `recentlyViewed` (local-only, no sync)
- Fields: `id`, `beanUrlPath`, `viewedAt`, `beanData`
- Indexed: `beanUrlPath`, `viewedAt`
- Not synced to server — purely local browsing history
- Managed by `trackBeanView()` and `getRecentlyViewedBeans()`

#### `tastings`
- Fields: `id`, `date`, `name`, `selectedNotes`, `beanUrlPath`, `beanData`, `syncId`, `updatedAt`, `deletedAt`, `syncedAt`, `ownerId`
- Indexed: `date`, `name`, `beanUrlPath`, `syncId`, `updatedAt`, `ownerId`
- Soft-delete: if `syncedAt` is set, records are marked with `deletedAt` instead of hard-deleted so deletions propagate to the server

#### `customBeans`
- Fields: `id`, `syncId`, `beanUrlPath`, `beanData`, `updatedAt`, `deletedAt`, `syncedAt`, `ownerId`
- Indexed: `beanUrlPath`, `syncId`, `updatedAt`, `ownerId`
- `beanData` stores the full `CoffeeBean` object as JSON

#### `savedBeans`
- Fields: `id`, `syncId`, `beanUrlPath`, `notes`, `beanData`, `createdAt`, `updatedAt`, `deletedAt`, `syncedAt`, `ownerId`
- Indexed: `syncId`, `beanUrlPath`, `ownerId`
- `syncId` is the nanoid assigned by the server on first save (different from tastings/customBeans where client generates UUIDs)

#### `brewRecipes`
- Fields: `id`, `syncId`, `beanUrlPath`, `recipeData`, `parameters`, `feedback`, `isSaved`, `lastUsedAt`, `createdAt`, `updatedAt`, `deletedAt`, `syncedAt`, `ownerId`
- Indexed: `syncId`, `beanUrlPath`, `ownerId`, `isSaved`, `lastUsedAt`
- Only recipes with `isSaved === true` are synced to the server

### Cross-Table Record Relationships

Custom beans are stored locally in `customBeans` with their full `CoffeeBean` data. When tasting sessions or saved beans reference a custom bean by `beanUrlPath` (paths starting with `/custom/`), the local code rehydrates `beanData` from the `customBeans` table rather than fetching from the public API. This is done in `getTastingHistory()` and `getTasting()`.

### Owner ID and Guest Data

- `getCurrentOwnerId()` reads from `localStorage` key `kissaten_current_user_id`
- Set during sync via `setCurrentOwnerId(userId)` after authentication
- Guest (unauthenticated) records have `ownerId === null`
- On first sync after login, `claimUnowned*()` functions assign all unowned local records to the current user via `bulkPut`
- Local queries filter by `ownerId === userId || !ownerId` to show both owned and guest records

### Reactive Updates (Svelte 5 Runes)

`frontend/src/lib/db/updates.svelte.ts` exports a `dbUpdateTrigger` `$state` object with counters for each table type. Sync functions and local CRUD helpers call `notifyUpdate('tastingHistory')` etc. to increment the counter, which triggers reactive re-reads in Svelte components that reference `dbUpdateTrigger`.

## Remote Database (Turso/libSQL via Drizzle)

### Connection

```typescript
// frontend/src/lib/server/database/index.ts
const client = createClient({ url: env.DATABASE_URL })
export const db = drizzle(client, { schema })
```

The server connects to Turso (or any libSQL-compatible database) using `DATABASE_URL`. Drizzle ORM maps the schema to SQLite tables.

### Server-Side Schema

| Table | PK | Key Columns | Sync-Specific Behavior |
|---|---|---|---|
| `saved_beans` | `id` (nanoid) | `userId`, `beanUrlPath`, `notes`, `createdAt`, `updatedAt` | Hard-delete (no `deletedAt` column); removals are permanent |
| `custom_beans` | `id` (`custom_<nanoid>`) | `userId`, `beanData` (JSON string), `updatedAt`, `deletedAt` | Soft-delete via `deletedAt` for sync propagation |
| `tasting_sessions` | `id` (client UUID) | `userId`, `data` (JSON string), `updatedAt`, `deletedAt` | Soft-delete; `data` stores the full `TastingSession` as JSON |
| `brew_recipes` | `id` (client UUID) | `userId`, `data` (JSON string), `updatedAt`, `deletedAt` | Soft-delete; only `isSaved` recipes are pushed |

Auth tables (`user`, `session`, `account`, `verification`) are managed by `better-auth`.

### Server Endpoints (SvelteKit `command`/`query`)

Each sync type exposes four server-side endpoints following the same pattern:

| Endpoint | Type | Purpose |
|---|---|---|
| `push*` | `command` (mutation) | Accepts an array of `{id, data, updatedAt, deletedAt}`; upserts each record using last-write-wins (LWW) on `updatedAt` |
| `pull*` | `query` (read) | Returns all records for the user updated since a `since` timestamp; includes `deletedAt` for soft-delete propagation |
| `get*Count` | `query` (read) | Returns count of non-deleted records for the user; used by `verifySyncConsistency` |
| `get*Digest` | `query` (read) | Returns SHA-256 hash of `id:updatedAt` pairs sorted by ID; used by `verifySyncConsistency` to detect content drift at equal counts |

Saved beans differ: they use individual `saveBean`/`unsaveBean`/`updateBeanNotes` commands instead of batch push, and `getSavedBeans` returns the full list (no `since` cursor) because the pull step does full reconciliation.

## Sync Protocol

### Sync Manager (`syncManager.svelte.ts`)

`runGlobalSync()` is the main entry point. It runs all four sync types in parallel via `Promise.allSettled` and aggregates results.

**Three sync modes:**

| Mode | Behavior |
|---|---|
| `'normal'` (default) | Incremental push + pull for all four tables using `since` cursors |
| `'verify-then-fix'` | Runs `verifySyncConsistency()` first; if any table drifts, force-full syncs only the affected tables |
| `'force-full'` | Unconditionally re-fetches everything for all four tables (ignores cursors) |

**Guard rails:**
- **Concurrency lock**: `syncState.isSyncing` prevents overlapping sync runs
- **Offline check**: `navigator.onLine` — skips sync entirely if offline
- **Silent vs. verbose**: When `silent: true` (default), toasts fire only on changes; when `silent: false`, a loading toast is shown and replaced with a summary
- **Auth error detection**: If all four syncs return `'Not authenticated'`, shows a "Sign in to sync" toast instead of an error

### Per-Table Sync Flow

Each sync type (except saved beans) follows the same push-then-pull pattern:

#### 1. Push Phase

```
Read local dirty records → Batch push to server → Mark as synced
```

- **Dirty predicate**: `!syncedAt || updatedAt > syncedAt` (modified since last sync)
- **Ownership filter**: `ownerId === userId || !ownerId`
- **Batching**: Tastings and brew recipes push in batches of 5; custom beans in batches of 50
- **Skinny sync for tastings**: `beanData` is stripped from the push payload (custom beans are mirrored separately; public beans are rehydrated on pull)
- **Error handling**: Network errors (`TypeError`/fetch failures) are caught and logged but don't block the pull phase; the push will retry on the next sync cycle

#### 2. Pull Phase

```
Fetch remote changes since cursor → Diff against local → Batch apply
```

- **Cursor**: Per-user `localStorage` key (e.g., `kissaten_last_tasting_sync_<userId>`)
- **Force-full**: When `forceFullSync: true`, cursor is reset to 0 so the server returns everything
- **Conflict resolution**: **Last-write-wins (LWW)** — if `remote.updatedAt > local.updatedAt`, the remote record overwrites the local one
- **Soft-delete propagation**: If `remote.deletedAt` is set, the local record is hard-deleted (it was already soft-deleted and pushed)
- **Bean rehydration**: Tastings and saved beans that arrive without `beanData` are rehydrated by:
  1. Checking the local `customBeans` mirror first
  2. Fetching remaining public beans via `api.fetchAllBeansByPaths()` (paginated, 100 paths per call)
- **Batch writes**: Uses `bulkAdd`, `bulkPut`, `bulkDelete` for atomicity; custom beans also deep-clone via `JSON.parse(JSON.stringify())` to strip Svelte proxy descriptors before IndexedDB writes
- **Timeout protection**: Custom bean sync wraps all DB operations in `withTimeout()` (5s) to prevent permanent store locking

### Saved Beans — Full Reconciliation (Different Pattern)

Saved beans use a different sync strategy than the other three tables:

- **Push**: Individual `saveBean()`, `unsaveBean()`, `updateBeanNotes()` calls (not batch push)
  - New saves: calls `saveBean` → gets back server `id` → stores as `syncId`
  - Soft-deletes: calls `unsaveBean` only if `syncedAt` was set (was previously pushed); then hard-deletes locally
  - Note updates: calls `updateBeanNotes` if `updatedAt > syncedAt`
- **Pull**: **Full reconciliation** every time — fetches the entire remote list and reconciles:
  - Remote records missing locally → add
  - Remote records newer than local → update
  - Synced local records missing from remote → delete (but only if `syncedAt` is set, protecting un-pushed guest edits)
  - Pre-existing local records without `beanData` → rehydrate from API or custom beans mirror

### Verification (`verifySync.ts`)

`verifySyncConsistency()` is a cheap, read-only consistency check that runs before `verify-then-fix` mode syncs:

1. **Count check**: Compare local count to remote count for each table
2. **Digest check**: If counts match, compute SHA-256 of `syncId:updatedAt` pairs (sorted by `syncId`) on both sides and compare
3. **Result**: Returns `{ ok, issues, skipped }` — any mismatch triggers a force-full sync for that table only

**Exclusions from digest:**
- Soft-deleted records
- Dirty (un-pushed) local records — `!syncedAt || updatedAt > syncedAt`
- Brew recipes where `isSaved !== true`

The server-side digest computation matches the client-side exactly: same sort order (by `syncId`), same join format (`id:updatedAt.getTime()`), same SHA-256 hash.

## Conflict Resolution Strategy

The system uses **last-write-wins (LWW)** based on `updatedAt` timestamps:

- On push: server only accepts a record if `incoming.updatedAt > existing.updatedAt`
- On pull: client only overwrites local if `remote.updatedAt > local.updatedAt`
- No field-level merging or CRDTs — the entire record (stored as a JSON blob in `data`/`beanData`) is replaced atomically

This is acceptable because:
1. User data records are small and infrequently edited
2. Most edits happen on a single device at a time
3. The verification system catches drift that LWW might miss

## Offline-First Behavior

- All reads come from Dexie (IndexedDB) — works fully offline
- Writes go to Dexie immediately with `syncedAt = null`
- Sync runs only when `navigator.onLine` is true
- Push failures (network errors) are non-fatal — dirty records remain and retry on next sync
- The service worker (`frontend/src/service-worker.ts`) enables PWA support for offline page loads

## Change-Oriented Guidance

### Adding a New Sync Type

1. Add a new table to the Dexie schema (new version in `localdb.ts`)
2. Add a corresponding Drizzle table in `schema.ts`
3. Create `*.remote.ts` with `push*`, `pull*`, `get*Count`, `get*Digest` endpoints
4. Create a sync module in `frontend/src/lib/sync/` following the `tastingSync.ts` pattern
5. Register the sync in `syncManager.svelte.ts`:
   - Add to the `Promise.allSettled` call
   - Add result aggregation
   - Add to the `forceFor` set for `'force-full'` mode
6. Add the type to `SyncType` in `verifySync.ts` and add a check entry
7. Add a `notifyUpdate` trigger key in `updates.svelte.ts`

### Common Pitfalls

- **Svelte proxy descriptors**: Svelte 5 runes mode creates proxy objects that can't be structured-cloned into IndexedDB. Always sanitize with `JSON.parse(JSON.stringify(obj))` before writes. The codebase does this in `saveBrewRecipe()`, `trackBeanView()`, and custom bean pull writes.
- **Dexie version change blocking**: If you add a new schema version, existing tabs with the old version will block the upgrade. The `versionchange` and `blocked` event handlers in `localdb.ts` close the connection to allow upgrades.
- **Un-pushed guest edits**: Never delete local records that have `!syncedAt` during reconciliation — they haven't been pushed yet. The saved beans sync explicitly guards against this.
- **Date serialization**: JSON turns `Date` objects into strings. Reading hooks on `tastings` and `recentlyViewed` rehydrate them. Pull code also manually converts string dates back to `Date` objects.
- **Timeout protection**: Custom bean sync uses `withTimeout()` on all Dexie operations to prevent the IndexedDB store from permanently locking. If adding new sync types, consider the same pattern.
