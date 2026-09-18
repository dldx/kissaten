import type { ApiCacheEntry } from "$lib/db/localdb";

/**
 * Layout option sets built from the three catalogue API payloads.
 *
 * These helpers live outside `(main)/+layout.ts` so the cache-vs-network
 * shapes can be unit-tested without pulling in `$lib/api` / Kit virtuals.
 */

/** Raw `{ success, data }` bodies from the three catalogue endpoints. */
export interface CatalogueJson {
  countries?: any;
  roasters?: any;
  roasterLocations?: any;
}

/** Build the layout option sets from raw `{ success, data }` API JSON bodies. */
export function buildOptions(json: CatalogueJson) {
  const originOptions =
    json.countries?.success && json.countries.data
      ? json.countries.data.map((country: any) => ({
          value: country.country_code,
          text: country.country_name || country.country_code,
        }))
      : [];

  const allRoasters =
    json.roasters?.success && json.roasters.data ? json.roasters.data : [];

  const roasterLocationOptions =
    json.roasterLocations?.success && json.roasterLocations.data
      ? json.roasterLocations.data.map((location: any) => ({
          value: location.code,
          text: `${location.location} (${location.roaster_count})`,
        }))
      : [];

  return { originOptions, allRoasters, roasterLocationOptions };
}

/**
 * Build layout options from Dexie cache entries. `getCached` returns
 * `ApiCacheEntry` wrappers — the raw `{ success, data }` body lives on
 * `.json`. Passing the wrappers straight to `buildOptions` reads
 * `wrapper.success` (undefined) and silently yields empty option arrays,
 * which is how the country badges regressed to two-letter codes.
 */
export function buildOptionsFromCache(
  countries: ApiCacheEntry,
  roasters: ApiCacheEntry,
  roasterLocations: ApiCacheEntry,
) {
  return buildOptions({
    countries: countries.json,
    roasters: roasters.json,
    roasterLocations: roasterLocations.json,
  });
}

/** True when a cache-built option set is complete enough to serve. */
export function hasUsableOptions(
  options: ReturnType<typeof buildOptions>,
): boolean {
  return (
    options.originOptions.length > 0 &&
    options.allRoasters.length > 0 &&
    options.roasterLocationOptions.length > 0
  );
}
