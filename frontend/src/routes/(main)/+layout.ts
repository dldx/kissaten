import { currencyState } from "$lib/stores/currency.svelte.js";
import { api } from "$lib/api";
import { cacheDep } from "$lib/offline/apiCache";
import { buildOptions } from "$lib/offline/layoutOptions";
import type { UserDefaults } from "$lib/types/userDefaults";

// Initialize the currency store so it's available everywhere
export async function load({ fetch, parent, data, depends }) {
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

  // Re-run this load when the offline wrapper's background revalidation
  // detects a change in one of the three catalogue payloads (post-hydration).
  depends(cacheDep("/api/v1/roasters"));
  depends(cacheDep("/api/v1/origins"));
  depends(cacheDep("/api/v1/roaster-locations"));

  // The api methods go through the offline cache wrapper: during hydration it
  // is network-first and serves the SSR-embedded response synchronously
  // (no flicker); afterwards it is cache-first with a background revalidation.
  // Offline client-side navigation with nothing cached can throw here (the SW
  // served a synthetic empty `__data.json` payload); fall back to an empty
  // app shell instead of throwing the whole layout (which would 500 every
  // route).
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
