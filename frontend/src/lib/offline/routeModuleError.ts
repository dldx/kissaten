export const ROUTE_MODULE_ERROR_MESSAGE =
  "Page could not be loaded. It will reload automatically once you are back online, or reload now to try again.";

// Both code-load failures (`import()` rejected by a failed module fetch) and
// data-load failures (`load_data`'s `__data.json` fetch rejecting at the
// network level, e.g. while the page is not yet under service-worker control)
// surface as one of these messages. `Failed to fetch` is the Chromium/Chrome
// form, `NetworkError when attempting to fetch resource.` Firefox's,
// `Load failed` Safari's.
const ROUTE_LOAD_ERROR_PATTERN =
  /Failed to fetch|error loading dynamically imported module|Importing a module script failed|NetworkError when attempting to fetch resource|Load failed|Internet connection appears to be offline/i;

export function isRouteModuleError(error: unknown): boolean {
  return error instanceof Error && ROUTE_LOAD_ERROR_PATTERN.test(error.message);
}

const RELOAD_GUARD_KEY = "kissaten:module-error-reload";

/**
 * Auto-reload recovery for route-load failures.
 *
 * A failed dynamic `import()` is remembered by the browser for the page
 * session, and a route whose code/data never loaded cannot be retried in
 * place, so the only way to retry is a reload. The failure can happen in the
 * window right after the `online` event fires but before Chromium's network
 * stack is usable again, so retry both on the `online` event and on mount
 * while already online. Guarded to at most one reload per URL (the guard
 * doubles as loop protection should the reload fail again); if sessionStorage
 * is unavailable the user keeps the manual Reload button.
 */
export function createModuleLoadReloader(isModuleError: () => boolean) {
  let reloading = false;

  const attempt = () => {
    if (reloading || !isModuleError()) return;
    reloading = true;
    try {
      if (sessionStorage.getItem(RELOAD_GUARD_KEY) === location.href) return;
      sessionStorage.setItem(RELOAD_GUARD_KEY, location.href);
    } catch {
      return; // no storage to guard against a loop — leave it to the user
    }
    location.reload();
  };

  return {
    /** Call from the window `online` listener. */
    onOnline: attempt,
    /** Call once on mount to retry when the connection is already back. */
    onMount: () => {
      if (navigator.onLine) attempt();
    },
  };
}