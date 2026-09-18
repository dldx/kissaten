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
 * Strategy (per the offline-first plan, Phase 2):
 * - cache-first: serve a fresh Dexie copy, background-refresh when stale-ish;
 *   fall back to stale cache when offline; throw `OfflineError` when nothing
 *   cached and the network is unreachable.
 * - network-first: prefer the network (drops straight to the DB store on
 *   success); serve stale cache only when the network fails. Used for detail
 *   pages where fresh data matters (bean detail, roaster detail, …).
 *
 * The cache key is the FULL url (path + query string, incl. `convert_to_currency`
 * when present) so currency variants and search pages are distinct entries.
 */

export const API_TTL: Record<"short" | "long", number> = {
  short: 60 * 60 * 1000, // search + stats
  long: 24 * 60 * 60 * 1000, // everything else
};

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
 * Fetch a url, serving from the Dexie `apiCache` table per the given mode.
 *
 * Returns the parsed JSON body plus a `stale` flag; callers that don't care
 * about staleness simply ignore it. Never swallows errors into `null` — throws
 * `OfflineError` only when nothing cached and the network failed.
 */
export async function fetchWithCache(
  url: string,
  fetchFn: typeof fetch,
  opts: { mode?: "cache-first" | "network-first" } = {},
): Promise<{ json: any; stale: boolean }> {
  const mode = opts.mode ?? "cache-first";

  // Server-side rendering / no IndexedDB → plain network passthrough.
  if (!isBrowserDbAvailable() || import.meta.env.SSR) {
    return { json: await networkJson(url, fetchFn), stale: false };
  }

  // Intrinsically volatile urls (random sorting) are never cached.
  if (url.includes("sort_order=random")) {
    return { json: await networkJson(url, fetchFn), stale: false };
  }

  const refresh = async () => {
    try {
      const json = await networkJson(url, fetchFn);
      await storeCached(url, json, ttlClassForUrl(url));
    } catch {
      // Background refresh is best-effort — ignore failures.
    }
  };

  if (mode === "cache-first") {
    // 1. Fresh cache hit → serve immediately, maybe background-refresh.
    try {
      const entry = await getCached(url);
      if (entry) {
        const ttl = API_TTL[entry.ttlClass ?? ttlClassForUrl(url)];
        const age = Date.now() - entry.savedAt;
        if (age < ttl) {
          if (age > ttl / 2) void refresh();
          return { json: entry.json, stale: false };
        }
      }
    } catch {
      // IndexedDB error → fall through to network below.
    }

    // 2. Network + store (new or stale entry).
    try {
      const json = await networkJson(url, fetchFn);
      void storeCached(url, json, ttlClassForUrl(url));
      return { json, stale: false };
    } catch {
      // 3. Network failed → stale cache of ANY age, else OfflineError.
      const cached = await getCached(url).catch(() => undefined);
      if (cached !== undefined) return { json: cached.json, stale: true };
      throw new OfflineError(url);
    }
  }

  // network-first: network wins, cache is the offline fallback.
  try {
    const json = await networkJson(url, fetchFn);
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
