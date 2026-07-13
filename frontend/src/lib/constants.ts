/**
 * Shared currency-related constants.
 *
 * The cookie name MUST stay in sync across every place that reads or writes
 * the user's currency preference. If SSR (server load / hooks) and client
 * (currencyState / hooks.client) ever disagree on the name, the
 * `convert_to_currency` URL param will diverge between SSR and hydration,
 * defeating SvelteKit's load-fetch deduplication and triggering a duplicate
 * API request. Import this constant everywhere instead of hardcoding it.
 */
export const CURRENCY_COOKIE_NAME = 'kissaten-currency';

/**
 * localStorage key holding the cached currency rate table
 * (`{ rates: Record<code, rate_to_usd>, fetchedAt: number }`).
 *
 * Rates are cached client-side so `currencyState.convert()` works
 * synchronously on repeat visits without waiting for the network. The TTL
 * mirrors the server's refresh threshold (`/api/v1/currencies/refresh` only
 * updates if rates are older than ~23h), so a client-side cache miss simply
 * triggers a background refresh.
 */
export const RATES_CACHE_KEY = 'kissaten-currency-rates';

/** How long cached rates are considered fresh. 23 hours, matching the server. */
export const RATES_TTL_MS = 23 * 60 * 60 * 1000;

/** Default currency used when no cookie is present (SSR and client agree on this). */
export const DEFAULT_CURRENCY = 'EUR';
