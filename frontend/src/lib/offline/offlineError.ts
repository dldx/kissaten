/**
 * User-facing offline error type.
 *
 * The message is intentionally free of API urls: it is rendered in load
 * fallbacks (`metadata.error`, `searchError`, …), in `+error.svelte` pages and
 * in `handleError`, so it must read like product copy, not a network log. The
 * technical url stays available as `error.url` for debugging.
 */

/** User-facing message for missing offline data (never includes the API url). */
export const OFFLINE_ERROR_MESSAGE =
  "You're offline and this content isn't available offline yet. Reconnect and try again.";

/** Thrown when a fetch fails and no cached copy exists for the url. */
export class OfflineError extends Error {
  constructor(
    public url: string,
    public cachedPayload?: any,
  ) {
    super(OFFLINE_ERROR_MESSAGE);
    this.name = "OfflineError";
  }
}

/** Type guard for `OfflineError`. */
export function isOfflineError(error: unknown): error is OfflineError {
  return error instanceof OfflineError;
}
