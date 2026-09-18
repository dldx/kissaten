import { browser } from "$app/environment";
import { db, getCurrentOwnerId } from "./localdb";
import { dbUpdateTrigger } from "./updates.svelte";

/**
 * Shared, module-level cache of "is this bean saved?" status, keyed by
 * `beanUrlPath`.
 *
 * Loaded exactly once per refresh — ONE `savedBeans.toArray()` + ONE
 * `customBeans.toArray()` — instead of per-card Dexie queries. Components
 * (SaveBeanButton, BeanActionButton, bean detail page) read the flat map
 * synchronously from `savedStatus.entries`.
 */
export type SavedStatusEntry = {
  savedBeanId: string;
  notes: string;
  isCustom: boolean;
};

export const savedStatus = $state<{
  entries: Record<string, SavedStatusEntry>;
  loaded: boolean;
  loading: boolean;
}>({
  entries: {},
  loaded: false,
  loading: false,
});

let lastKey = "";
let inFlight: Promise<void> | null = null;
let pendingKey: string | null = null;

/**
 * Call from a component `$effect`. Reads `dbUpdateTrigger` synchronously so
 * the calling effect re-runs when data changes (local saves/unsaves, sync,
 * login/logout). Only touches Dexie in the browser.
 */
export function ensureSavedStatus(): void {
  if (!browser) return;
  const userId = getCurrentOwnerId();
  const key = `${dbUpdateTrigger.savedBeans}:${dbUpdateTrigger.customBeans}:${userId ?? ""}`;
  if (savedStatus.loaded && key === lastKey) return;
  if (inFlight) {
    pendingKey = key;
    return;
  }
  void runRefresh(key, userId);
}

async function runRefresh(key: string, userId: string | null): Promise<void> {
  savedStatus.loading = true;
  const refresh = (async () => {
    const [saved, custom] = await Promise.all([
      db.savedBeans.toArray(),
      db.customBeans.toArray(),
    ]);
    const entries: Record<string, SavedStatusEntry> = {};
    for (const s of saved) {
      if (!s.deletedAt && (s.ownerId === userId || !s.ownerId || !userId)) {
        entries[s.beanUrlPath] = {
          savedBeanId: s.syncId,
          notes: s.notes || "",
          isCustom: false,
        };
      }
    }
    for (const c of custom) {
      if (
        !c.deletedAt &&
        (c.ownerId === userId || !c.ownerId || !userId) &&
        !entries[c.beanUrlPath]
      ) {
        entries[c.beanUrlPath] = {
          savedBeanId: c.syncId,
          notes: "",
          isCustom: true,
        };
      }
    }
    savedStatus.entries = entries; // replace whole object so consumers re-derive
    savedStatus.loaded = true; // only set loaded on success
    lastKey = key;
  })();
  inFlight = refresh;
  try {
    await refresh;
  } catch (e) {
    console.error("savedStatus refresh failed", e);
  } finally {
    savedStatus.loading = false;
    inFlight = null;
    if (pendingKey && pendingKey !== lastKey) {
      const k = pendingKey;
      pendingKey = null;
      const u = getCurrentOwnerId();
      void runRefresh(k, u);
    }
  }
}