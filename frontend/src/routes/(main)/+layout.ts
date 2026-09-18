import { currencyState } from "$lib/stores/currency.svelte.js";
import { api } from "$lib/api";
import { getCached } from "$lib/offline/apiCache";
import {
  buildOptions,
  buildOptionsFromCache,
  hasUsableOptions,
} from "$lib/offline/layoutOptions";
import type { UserDefaults } from "$lib/types/userDefaults";

// Network fetch of the three catalogue payloads; the api methods go through
// the offline cache wrapper, so a successful refresh also re-populates Dexie.
async function refreshCatalogueData(
  fetch: typeof globalThis.fetch,
): Promise<void> {
  try {
    await Promise.all([
      api.getCountries(fetch),
      api.getRoasters(fetch),
      api.getRoasterLocations(fetch),
    ]);
  } catch (error) {
    console.warn("Background layout data refresh failed:", error);
  }
}

// Initialize the currency store so it's available everywhere
export async function load({ fetch, parent, data }) {
  // Pick up parent (root) layout data so it propagates to children.
  const parentData = await parent();

  // `data` is the sibling `+layout.server.ts` return — `currency` (cookie)
  // and `userDefaults.roasterLocations` (server-loaded via the
  // `getUserDefaultRoasterLocations` remote query). Layout data merges
  // down to children automatically, but we surface `userDefaults`
  // explicitly so the type is non-optional for consumers. `data` itself can
  // be undefined on synthetic navigation when the SW served an empty
  // `{ nodes: [] }` payload — hence the optional chaining + default.
  const userDefaults: UserDefaults = data?.userDefaults ?? {
    roasterLocations: [],
  };

  // The currency store is already initialized in its constructor
  // This ensures it's loaded at the root layout level

  // Client-side: serve the three catalogue payloads instantly from Dexie
  // when all are cached, then refresh in the background. This degates the
  // network round-trip that currently gates every route.
  if (!import.meta.env.SSR) {
    try {
      const [countries, roasters, roasterLocations] = await Promise.all([
        getCached("/api/v1/origins"),
        getCached("/api/v1/roasters"),
        getCached("/api/v1/roaster-locations"),
      ]);
      if (countries && roasters && roasterLocations) {
        const options = buildOptionsFromCache(
          countries,
          roasters,
          roasterLocations,
        );
        // Unusable cache (missing/corrupt payloads) must not overwrite the
        // server-rendered options with empty arrays — fall through to network.
        if (hasUsableOptions(options)) {
          // Fire-and-forget background refresh (network + re-store).
          setTimeout(() => void refreshCatalogueData(fetch), 0);
          return {
            ...parentData,
            currencyState,
            ...options,
            userDefaults,
          };
        }
      }
    } catch (error) {
      // Cache read failed — fall through to the normal network path.
      console.warn("Layout cache read failed, using network:", error);
    }
  }

  // Server-side (SSR) or any-missing-cache: the normal network path. The api
  // methods still go through the wrapper, so successful fetches are stored.
  // Offline client-side navigation with nothing cached can throw here (the SW
  // served a synthetic empty `__data.json` payload); fall back to an empty
  // app shell instead of throwing the whole layout (which would 500 every
  // route). The client cache-first branch above stays unchanged.
  try {
    const [countriesResponse, roastersResponse, roasterLocationsResponse] =
      await Promise.all([
        api.getCountries(fetch),
        api.getRoasters(fetch),
        api.getRoasterLocations(fetch),
      ]);

    const options = buildOptions({
      countries: countriesResponse,
      roasters: roastersResponse,
      roasterLocations: roasterLocationsResponse,
    });
    return {
      ...parentData,
      currencyState,
      ...options,
      userDefaults,
    };
  } catch (error) {
    console.warn(
      "Layout network data load failed, rendering empty shell:",
      error,
    );
    return {
      ...parentData,
      currencyState,
      originOptions: [],
      allRoasters: [],
      roasterLocationOptions: [],
      userDefaults,
    };
  }
}
