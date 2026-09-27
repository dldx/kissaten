import {
  db,
  type ApiCacheEntry,
  type CatalogueBeanEntry,
} from "$lib/db/localdb";
import { OfflineError } from "./offlineError";

export {
  OFFLINE_ERROR_MESSAGE,
  OfflineError,
  isOfflineError,
} from "./offlineError";

/**
 * Offline-first cache wrapper for `KissatenAPI` GET calls.
 *
 * Strategy (hydration-gated stale-while-revalidate):
 * - During the initial client hydration pass (`hydrating` is true) the default
 *   mode is **network-first**. This is cheap: SvelteKit's `initial_fetch`
 *   serves the response embedded in the SSR HTML synchronously, so the
 *   hydration re-run of a universal load sees fresh SSR data with no real
 *   network round-trip and no flicker. Concurrent loads for the same URL are
 *   deduped (the embedded response is single-use).
 * - After hydration (`markHydrated`) the default is **cache-first**: a fresh
 *   Dexie copy renders instantly and a throttled, deduped background
 *   revalidation refreshes it. If the payload changed, it is persisted and
 *   `invalidate('app:cache:<url>')` is fired (dynamically imported, browser
 *   only) so loads that registered the matching `depends(...)` re-run.
 * - An explicit `opts.mode` always wins. Network failures fall back to stale
 *   cache; nothing cached + offline throws `OfflineError`.
 *
 * The cache key is the FULL url (path + query string, incl. `convert_to_currency`
 * when present) so currency variants and search pages are distinct entries.
 */

export const API_TTL: Record<"short" | "long", number> = {
  short: 60 * 60 * 1000, // search + stats
  long: 24 * 60 * 60 * 1000, // everything else
};

/**
 * Minimum time between background revalidations of the same URL. Every fresh
 * cache-first hit schedules a revalidation, but the throttle keyed on the last
 * *successful* revalidation caps the network traffic to at most this often.
 */
export const REVALIDATE_THROTTLE_MS = 2 * 60 * 1000;

/** True until the first client navigation after hydration flips the gate. */
let hydrating = typeof window !== "undefined";

/** Flip the hydration gate; called from `afterNavigate` once after hydration. */
export function markHydrated(): void {
  hydrating = false;
}

/** Whether the initial client hydration pass is still in progress. */
export function isHydrating(): boolean {
  return hydrating;
}

/**
 * SvelteKit invalidate dependency for a cached URL. Matches the `depends(...)`
 * registered by the loads that read the URL, so a changed revalidation
 * re-runs exactly those loads.
 */
export function cacheDep(url: string): `${string}:${string}` {
  return `app:cache:${url}` as `${string}:${string}`;
}

/**
 * Effective cache mode: an explicit mode wins, otherwise the hydration gate
 * decides (network-first while hydrating, cache-first afterwards).
 */
export function selectMode(
  explicit: "cache-first" | "network-first" | undefined,
  hydratingNow: boolean,
): "cache-first" | "network-first" {
  return explicit ?? (hydratingNow ? "network-first" : "cache-first");
}

/** Serialize a payload for equality checks between cached and revalidated data. */
export function serializePayload(json: unknown): string {
  return JSON.stringify(json) ?? "null";
}

/** In-flight network fetches per URL (shared by hydration + revalidation). */
const inflightNetwork = new Map<string, Promise<any>>();
/** In-flight background revalidations per URL (dedupe). */
const inflightRevalidation = new Map<string, Promise<void>>();
/** Last successful revalidation time per URL (throttle key). */
const lastRevalidatedAt = new Map<string, number>();

/** Short TTL for search and stats endpoints; long for everything else. */
export function ttlClassForUrl(url: string): "short" | "long" {
  if (url.includes("/api/v1/search") || url.includes("/api/v1/stats"))
    return "short";
  return "long";
}

/**
 * Whether IndexedDB is available in this JS context. Swallow the `indexedDB`
 * access itself (some environments throw on property access) and return false
 * on the server.
 */
export function isBrowserDbAvailable(): boolean {
  try {
    return typeof indexedDB !== "undefined" && typeof window !== "undefined";
  } catch {
    return false;
  }
}

/** Raw network fetch + JSON parse, preserving the app's current error shape. */
async function networkJson(url: string, fetchFn: typeof fetch): Promise<any> {
  const r = await fetchFn(url);
  if (!r.ok) throw new Error(`HTTP error! status: ${r.status}`);
  return r.json();
}

/**
 * Network fetch + JSON parse deduped per URL. Concurrent callers share one
 * fetch — essential during hydration, where SvelteKit's embedded SSR response
 * is single-use (the first `initial_fetch` removes the script tag), so a
 * second caller would otherwise hit the real network.
 */
function networkJsonOnce(url: string, fetchFn: typeof fetch): Promise<any> {
  const existing = inflightNetwork.get(url);
  if (existing) return existing;

  const task = networkJson(url, fetchFn);
  inflightNetwork.set(url, task);
  const clear = () => {
    if (inflightNetwork.get(url) === task) inflightNetwork.delete(url);
  };
  // Handle both settle paths so the cleanup chain never rejects unhandled.
  void task.then(clear, clear);
  return task;
}

/**
 * Notify SvelteKit subscribers that a cached URL changed. `$app/navigation` is
 * client-only, so it is imported dynamically from this browser-guarded
 * function — never at module top level (this module is imported by universal
 * loads that also execute during SSR).
 */
async function notifyCacheChanged(url: string): Promise<void> {
  if (!isBrowserDbAvailable()) return;
  try {
    const { invalidate } = await import("$app/navigation");
    await invalidate(cacheDep(url));
  } catch (error) {
    console.warn("Failed to invalidate cached url:", error);
  }
}

/**
 * Schedule a throttled, deduped background revalidation for a fresh
 * cache-first hit. On a changed payload it persists the new body and fires the
 * cache invalidation; on an unchanged payload it still refreshes `savedAt`
 * (via `storeCached`) but does not notify. Failures are ignored and leave the
 * throttle untouched so a later visit retries.
 */
function scheduleRevalidation(url: string, fetchFn: typeof fetch): void {
  if (inflightRevalidation.has(url)) return;

  const last = lastRevalidatedAt.get(url);
  if (last !== undefined && Date.now() - last < REVALIDATE_THROTTLE_MS) return;

  const task = (async () => {
    try {
      const json = await networkJsonOnce(url, fetchFn);
      const cached = await getCached(url);
      const changed =
        cached === undefined ||
        serializePayload(cached.json) !== serializePayload(json);
      await storeCached(url, json, ttlClassForUrl(url));
      lastRevalidatedAt.set(url, Date.now());
      if (changed) await notifyCacheChanged(url);
    } catch {
      // Background revalidation is best-effort — ignore failures.
    } finally {
      inflightRevalidation.delete(url);
    }
  })();

  inflightRevalidation.set(url, task);
}

/**
 * Fetch a url, serving from the Dexie `apiCache` table per the effective mode
 * (see the module doc comment). Returns the parsed JSON body plus a `stale`
 * flag; callers that don't care about staleness simply ignore it. Never
 * swallows errors into `null` — throws `OfflineError` only when nothing cached
 * and the network failed.
 */
export async function fetchWithCache(
  url: string,
  fetchFn: typeof fetch,
  opts: { mode?: "cache-first" | "network-first" } = {},
): Promise<{ json: any; stale: boolean }> {
  const mode = selectMode(opts.mode, hydrating);

  // Server-side rendering / no IndexedDB → plain network passthrough.
  if (!isBrowserDbAvailable() || import.meta.env.SSR) {
    return { json: await networkJson(url, fetchFn), stale: false };
  }

  // Intrinsically volatile urls (random sorting) are never cached.
  if (url.includes("sort_order=random")) {
    return { json: await networkJson(url, fetchFn), stale: false };
  }

  if (mode === "cache-first") {
    // 1. Fresh cache hit → serve immediately + throttled background refresh.
    try {
      const entry = await getCached(url);
      if (entry) {
        const ttl = API_TTL[entry.ttlClass ?? ttlClassForUrl(url)];
        const age = Date.now() - entry.savedAt;
        if (age < ttl) {
          scheduleRevalidation(url, fetchFn);
          return { json: entry.json, stale: false };
        }
      }
    } catch {
      // IndexedDB error → fall through to network below.
    }

    // 2. Network + store (new or stale entry).
    try {
      const json = await networkJsonOnce(url, fetchFn);
      void storeCached(url, json, ttlClassForUrl(url));
      return { json, stale: false };
    } catch {
      // 3. Network failed → stale cache of ANY age, else OfflineError.
      const cached = await getCached(url).catch(() => undefined);
      if (cached !== undefined) return { json: cached.json, stale: true };
      throw new OfflineError(url);
    }
  }

  // network-first: network wins (deduped), cache is the offline fallback.
  try {
    const json = await networkJsonOnce(url, fetchFn);
    void storeCached(url, json, ttlClassForUrl(url));
    return { json, stale: false };
  } catch {
    const cached = await getCached(url).catch(() => undefined);
    if (cached !== undefined) return { json: cached.json, stale: true };
    throw new OfflineError(url);
  }
}

/** Thin `db.apiCache.get` wrapper (never throws). */
export async function getCached(
  url: string,
): Promise<ApiCacheEntry | undefined> {
  if (!isBrowserDbAvailable()) return undefined;
  try {
    return await db.apiCache.where("key").equals(url).first();
  } catch (error) {
    console.warn("Error reading API cache:", error);
    return undefined;
  }
}

/** Thin `db.apiCache.put` wrapper (never throws). */
export async function storeCached(
  url: string,
  json: any,
  ttlClass: "short" | "long",
): Promise<void> {
  if (!isBrowserDbAvailable()) return;
  try {
    await db.apiCache.put({ key: url, json, savedAt: Date.now(), ttlClass });
  } catch (error) {
    // IndexedDB full / private mode must not break the app.
    console.warn("Error storing API cache:", error);
  }
}

/**
 * Return the most recently saved cache entry whose key starts with `prefix`
 * (e.g. `/api/v1/search?`). Used for "latest version of this search" fallbacks.
 */
export async function findCachedByPrefix(
  prefix: string,
): Promise<ApiCacheEntry | undefined> {
  if (!isBrowserDbAvailable()) return undefined;
  try {
    const entries = await db.apiCache
      .where("key")
      .startsWith(prefix)
      .sortBy("savedAt");
    return entries.length > 0 ? entries[entries.length - 1] : undefined;
  } catch (error) {
    console.warn("Error searching API cache by prefix:", error);
    return undefined;
  }
}

/**
 * Find the most recent cached `/api/v1/search` response that filtered on a
 * specific roaster name — used as the offline fallback for roaster detail
 * bean listings. Key ordering varies (currency param, pagination), so we scan
 * the index (only ~tens of entries) rather than rely on a key prefix.
 */
export async function findLatestSearchForRoaster(
  roasterName: string,
): Promise<ApiCacheEntry | undefined> {
  if (!isBrowserDbAvailable()) return undefined;
  try {
    const encoded = encodeURIComponent(roasterName);
    const all = await db.apiCache.toArray();
    const matches = all.filter(
      (e) =>
        e.key.startsWith("/api/v1/search") &&
        e.key.includes(`roaster=${encoded}`),
    );
    if (matches.length === 0) return undefined;
    matches.sort((a, b) => b.savedAt - a.savedAt);
    return matches[0];
  } catch (error) {
    console.warn("Error finding cached search for roaster:", error);
    return undefined;
  }
}

/** Most recent catalogue bean snapshots, newest first (up to `limit`). */
export async function listCachedBeanSnapshots(
  limit: number,
): Promise<CatalogueBeanEntry[]> {
  if (!isBrowserDbAvailable()) return [];
  try {
    return await db.catalogueBeans
      .orderBy("savedAt")
      .reverse()
      .limit(limit)
      .toArray();
  } catch (error) {
    console.warn("Error listing cached bean snapshots:", error);
    return [];
  }
}

/**
 * Offline bean-detail fallback: the catalogue snapshot for `beanUrlPath`,
 * preferring the newer of `catalogueBeans` and `recentlyViewed` (which also
 * stores full bean data when a bean page was visited).
 */
export async function getBeanSnapshot(
  beanUrlPath: string,
): Promise<CatalogueBeanEntry | undefined> {
  if (!isBrowserDbAvailable()) return undefined;
  try {
    const [catalogue, viewed] = await Promise.all([
      db.catalogueBeans
        .where("beanUrlPath")
        .equals(beanUrlPath)
        .first()
        .catch(() => undefined),
      db.recentlyViewed
        .where("beanUrlPath")
        .equals(beanUrlPath)
        .first()
        .catch(() => undefined),
    ]);
    const viewedTs = viewed ? new Date(viewed.viewedAt).getTime() : 0;
    // Prefer the newer of the catalogue snapshot and the recently-viewed
    // entry (recentlyViewed also carries full bean data once a page loads).
    if (!catalogue) {
      if (!viewed) return undefined;
      return { beanUrlPath, beanData: viewed.beanData, savedAt: viewedTs };
    }
    if (viewedTs > catalogue.savedAt) {
      return { beanUrlPath, beanData: viewed!.beanData, savedAt: viewedTs };
    }
    return catalogue;
  } catch (error) {
    console.warn("Error reading bean snapshot:", error);
    return undefined;
  }
}
