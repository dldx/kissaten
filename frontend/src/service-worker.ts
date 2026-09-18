/// <reference types="@sveltejs/kit" />
import { build, files, version } from "$service-worker";

/*
 * Phase 2.6 spike: how SvelteKit's client router handles a failed `__data.json`
 * fetch during client-side navigation. Source: `@sveltejs/kit` 2.50.1,
 * `node_modules/@sveltejs/kit/src/runtime/client/client.js`.
 *
 * R1 — what happens when the `__data.json` fetch fails (network error):
 *   `load_route` fetches serialized server data at client.js:1067
 *   (`server_data = await load_data(url, invalid_server_nodes)`). Any throw —
 *   including a network TypeError from `window.fetch` at client.js:2877 — is
 *   caught at client.js:1068 and routed to `load_root_error_page`
 *   (client.js:1075-1080). This app's root layout has no server load
 *   (`server_loads` is `[2]`, so `app.server_loads[0] === 0` is false at
 *   client.js:1272), so `load_root_error_page` does NOT refetch data; it
 *   renders `[root_layout, root_error]` (client.js:1317-1324) where
 *   `root_error = default_error_loader = _app.nodes[1]` (client.js:325) — the
 *   root `+error.svelte`. So an offline client-side nav lands on the *root*
 *   error page (no crash, no silent stay-on-page), and `(main)/+error.svelte`
 *   is NOT consulted for the pure `__data.json` failure. Errors thrown by the
 *   route's own universal `load` (e.g. the bean page throwing `error(404)`
 *   when the stale Dexie snapshot is missing) go through
 *   `load_nearest_error_page` (client.js:1232) and DO render
 *   `(main)/+error.svelte` (client.js:1193-1202).
 *
 * R2 — null node entries + re-running universal loads:
 *   The response `nodes` array is zipped positionally with the route's known
 *   `loaders` (`server_data_nodes?.[i]`, client.js:1099). A `null`/missing
 *   entry is tolerated with NO length validation: `create_data_node(null)`
 *   returns null (client.js:961-965), the server-data slot becomes null, and
 *   the node's universal `load` STILL runs client-side (the
 *   `node.universal?.load` block at client.js:768 ff). Excess nodes are
 *   ignored; short arrays are fine.
 *
 * R3 — can the SW know the correct node count for an arbitrary URL?
 *   No. The loaders list is derived from the bundled CSR route manifest
 *   (`routes` parsed from `_app` at client.js:318; `loaders = [...layouts,
 *   leaf]` at client.js:1025) which is computed inside the app bundle at
 *   runtime. The SW has no access to it, and URL→node ordering isn't derivable
 *   from the URL alone (optional layout groups, dynamic segments).
 *
 * DECISION: do NOT synthesize `{"type":"data","nodes":[...]}` in the SW. A
 *   wrong-length null-node payload would deserialize client-side, but the
 *   client would re-run every universal load against absent server data
 *   (streamed `dataPromise`s, server-load seeds) — a worse state than a clean
 *   offline page. Instead: (1) generic GETs are cached network-first (step g)
 *   which stores visited routes' `__data.json`, making client-side navigation
 *   to previously-visited routes work fully offline; (2) unvisited routes fall
 *   through to the SW navigation fallback and a styled offline-aware error
 *   page (`src/routes/+error.svelte` — the node `load_root_error_page`
 *   serves, plus `(main)/+error.svelte` for load-throwing routes); (3) hard
 *   navigations offline get the cached `/` app shell (step c), never a bare
 *   408.
 *
 * DECISION (REVISED): synthesize `{"type":"data","nodes":[],"uses":{}}` for
 *   offline-uncached `__data.json` (see branch h below). This reverses the
 *   original R2-based caution for three reasons: (a) the client tolerates
 *   absent/short `nodes` arrays — a missing entry just means that node's
 *   universal `load` re-runs client-side against `data: undefined`, and those
 *   loads now hit the Dexie cache wrapper; (b) every route load that consumes
 *   the `data` param (`(main)/+layout.ts`, `(main)/search/+page.ts`) was made
 *   null-safe, so `data?.x ?? default` instead of a throw; and (c) hover
 *   preloading is disabled while offline via a live `<body>` attribute toggle
 *   (`(main)/+layout.svelte` sets `data-sveltekit-preload-data="off"`), so the
 *   DEV-only "Preloading data ... failed: Internal Error" warning path is
 *   moot. That "Internal Error" came from the generic branch's bare 408:
 *   `load_data` gets a non-JSON 408 → `HttpError(408, undefined)` →
 *   `create_unexpected_error(..., undefined)` defaults the message to
 *   'Internal Error'. The new `__data.json` branch never returns a 408 for
 *   data. Network-first caching (keyed by pathname only) still stores visited
 *   routes' real payloads so they serve fully offline regardless of the
 *   `invalidation=` / `trailing_slash=` query noise the client appends.
 *
 * OFFLINE MANAGER REVIEW (dev fragility — fixed below):
 *   D1 — every `vite dev` start produced a new `version` (Kit defaults it to
 *   `Date.now()`), so cache names changed per restart and `activate` (which
 *   kept only SHELL) wiped PAGES/IMAGES: every cached navigation, API
 *   payload, `__data.json` and module chunk was lost on restart. The next
 *   offline click then had no route code to import →
 *   `net::ERR_INTERNET_DISCONNECTED` / "Failed to fetch dynamically imported
 *   module". Dev now uses stable `shell-dev`/`pages-dev`/`images-dev` names
 *   that survive restarts (legacy versioned names are deleted once).
 *   D2 — in dev `$service-worker`'s `build` is empty (a production build
 *   lists the whole Vite client manifest and precaches all route chunks), so
 *   nothing precached route code. Install now precaches the generated client
 *   modules (entry, root, matchers, per-node chunks) and each node's direct
 *   imports (the per-route `+page.svelte`/`+page.ts` and `+error.svelte`
 *   modules) under pathname-only keys; dev module requests stay network-first
 *   (HMR freshness) and fall back to those keys when the network fails.
 *   Remaining dev limitation: a route's deeper transitive modules accumulate
 *   from browsing (they persist in `pages-dev`); production has no such gap.
 *   D3 — a failed dynamic `import()` poisons the module map for the page
 *   session, so after reconnecting only a reload can load that route. The
 *   error pages detect the module-load failure and auto-reload on `online`.
 *   Note the `online` event can fire just before Chromium's network stack is
 *   usable again; with route code cached (D1/D2) the SW serves it from cache
 *   during that window instead of failing the import.
 */

// Dev detection: `build` is empty under `vite dev` (Kit serves every route
// chunk on demand), while a production build lists the whole Vite client
// manifest (see Kit's `build/build_service_worker.js`), i.e. every route
// chunk and asset.
const DEV = build.length === 0;

// Cache names. Production uses `version` (a per-build timestamp) so `activate`
// can wipe stale data on deploy. In DEV `version` is `Date.now()` evaluated
// per dev-server start, so versioned names would wipe ALL runtime caches
// (navigations, API payloads, `__data.json`, module chunks) on every restart —
// exactly when the next offline click needs them. Dev therefore uses stable
// names and never wipes them.
const SHELL = DEV ? "shell-dev" : `shell-${version}`;
const PAGES = DEV ? "pages-dev" : `pages-${version}`;
const IMAGES = DEV ? "images-dev" : `images-${version}`;
const KEEP = [SHELL, PAGES, IMAGES];

// Dev module URLs (Vite serves them on demand). They are network-first so
// edits/HMR stay fresh; the install precache is only a PATHNAME-keyed offline
// fallback (their `?t=` cache-busting queries change between fetches).
const DEV_MODULE_PATH =
  /^\/(?:src|@fs|@id|node_modules|\.svelte-kit\/generated)\//;

// Everything in `static` is precached EXCEPT `/data/*`. The only file there is
// `optimized_origins.json` (~4.3 MB): there are zero references to it in
// `frontend/src`, and precaching it bloats the install. The user decided to
// KEEP the file on disk, so it is just excluded from the precache glob
// (verified against built output: `files` entries are literal paths like
// `/data/optimized_origins.json`, `/manifest.json`, `/textures/...`).
const ASSETS = [
  ...build, // the app itself
  ...files.filter((f) => !f.startsWith("/data/")), // everything in `static`, minus /data/*
];

// Minimal offline document served as the last-resort navigation fallback —
// a friendly page instead of the bare 408 text response.
const OFFLINE_HTML = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Offline | Kissaten</title>
<style>
  body { font-family: system-ui, -apple-system, sans-serif; background: #0a0b1f; color: #faf6f3; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
  .card { text-align: center; padding: 2rem; }
  h1 { font-size: 1.5rem; margin-bottom: 0.5rem; }
  p { color: #94a3b8; margin: 0 0 1.5rem; }
  a { color: #f59e0b; font-weight: 600; }
</style>
</head>
<body>
<div class="card">
  <h1>You're offline</h1>
  <p>Reconnect to continue browsing Kissaten.</p>
  <a href="javascript:location.reload()">Try again</a>
</div>
<script>
  window.addEventListener("online", () => location.reload());
</script>
</body>
</html>`;

// TTL for the API stale-while-revalidate layer: 1h for search/stats, 24h for lists.
function apiTtl(url: URL): number {
  return url.pathname.includes("/api/v1/search") ||
    url.pathname.includes("/api/v1/stats")
    ? 60 * 60 * 1000
    : 24 * 60 * 60 * 1000;
}

/**
 * Fire-and-forget LRU eviction for the IMAGES cache, called after every
 * successful image put. When storage usage exceeds 70% of quota, delete the
 * oldest entries (tracked via `__img-meta` marker responses) until usage drops
 * below 70% or 25 entries have been removed. Everything is best-effort.
 */
async function maybeEvictImages(): Promise<void> {
  try {
    const estimate = await navigator.storage.estimate();
    if (!estimate.usage || !estimate.quota) return;
    const usage = estimate.usage;
    const quota = estimate.quota;
    if (usage / quota <= 0.7) return;

    const cache = await caches.open(IMAGES);
    const keys = await cache.keys();
    const metaPaths = keys
      .map((k) => new URL(k.url).pathname)
      .filter((p) => p.startsWith("/__img-meta"));

    const entries: { path: string; imagePath: string; t: number }[] = [];
    for (const path of metaPaths) {
      try {
        const metaRes = await cache.match(
          new URL(path, self.location.origin).href,
        );
        if (!metaRes) continue;
        const meta = (await metaRes.json().catch(() => null)) as {
          t?: number;
        } | null;
        if (!meta || typeof meta.t !== "number") continue;
        entries.push({
          path,
          imagePath: path.slice("/__img-meta".length),
          t: meta.t,
        });
      } catch {
        // unreadable meta — skip
      }
    }
    entries.sort((a, b) => a.t - b.t);

    let deleted = 0;
    for (const entry of entries) {
      if (deleted >= 25) break;
      const metaUrl = new URL(entry.path, self.location.origin).href;
      const imageUrl = new URL(entry.imagePath, self.location.origin).href;
      await cache.delete(metaUrl);
      // The image may be cached under query-variants (cf resize params) —
      // delete every key whose pathname matches.
      const imageKeys = keys.filter(
        (k) => new URL(k.url).pathname === entry.imagePath,
      );
      await Promise.all(imageKeys.map((k) => cache.delete(k)));
      deleted += 1;

      const re = await navigator.storage.estimate();
      if (re.usage && re.quota && re.usage / re.quota <= 0.7) break;
    }
  } catch {
    // Eviction is best-effort — never break the fetch path.
  }
}

// Helper function to resize image using OffscreenCanvas
async function resizeImage(blob: Blob, maxWidth: number, maxHeight: number): Promise<Blob> {
	const bitmap = await createImageBitmap(blob);

	let { width, height } = bitmap;
	const ratio = Math.min(maxWidth / width, maxHeight / height);

	if (ratio < 1) {
		width *= ratio;
		height *= ratio;
	}

	const canvas = new OffscreenCanvas(width, height);
	const ctx = canvas.getContext('2d');
	if (!ctx) throw new Error('Could not get canvas context');

	ctx.drawImage(bitmap, 0, 0, width, height);

	return await canvas.convertToBlob({
		type: 'image/jpeg',
		quality: 0.9
	});
}

// Helper to store image in IndexedDB
async function storeImageInDB(blob: Blob, key: string): Promise<void> {
	return new Promise((resolve, reject) => {
		const request = indexedDB.open('SharedImagesDB', 1);

		request.onerror = () => reject(request.error);

		request.onupgradeneeded = (event) => {
			const db = (event.target as IDBOpenDBRequest).result;
			if (!db.objectStoreNames.contains('images')) {
				db.createObjectStore('images');
			}
		};

		request.onsuccess = () => {
			const db = request.result;
			const transaction = db.transaction(['images'], 'readwrite');
			const store = transaction.objectStore('images');
			const putRequest = store.put(blob, key);

			putRequest.onsuccess = () => resolve();
			putRequest.onerror = () => reject(putRequest.error);

			transaction.oncomplete = () => db.close();
		};
	});
}

/**
 * Dev-only: production installs precache every built client chunk because
 * Kit puts the whole Vite client manifest into `$service-worker`'s `build`.
 * Under `vite dev` `build` is empty, so mirror what we can enumerate: the
 * generated client entry, root, matchers, one module per route node, and each
 * node's direct absolute-path imports (the per-route `+page.svelte`/`+page.ts`
 * and the `+error.svelte` modules). Those route-unique modules are exactly
 * what a never-visited route or an error page needs offline; their own
 * imports are shared modules normally cached by browsing.
 *
 * Everything is stored under PATHNAME-ONLY keys because dev module URLs carry
 * changing `?t=` timestamps; branch (g) serves them network-first (so edits
 * and HMR stay fresh) and only falls back to these keys when the network
 * fails. Best-effort: a failure here must never break install.
 */
async function cacheDevModule(shell: Cache, url: string): Promise<void> {
  try {
    const response = await fetch(url);
    if (!response.ok) return;
    const key = new URL(url, self.location.origin).pathname;
    await shell.put(key, response);
  } catch {
    // Best-effort: dev precache must never break install.
  }
}

async function precacheDevClientModules(shell: Cache): Promise<void> {
  const appUrl = "/.svelte-kit/generated/client/app.js";
  try {
    await cacheDevModule(shell, appUrl);
    const app = await shell.match(appUrl);
    if (!app) return;
    const source = await app.text();
    const nodeIds = new Set<string>();
    // Vite rewrites the generated imports to absolute URLs with cache-busting
    // queries, e.g. `import("/.svelte-kit/generated/client/nodes/3.js?t=...")`;
    // match the node id anywhere in the specifier.
    for (const match of source.matchAll(/nodes\/(\d+)\.js/g)) {
      nodeIds.add(match[1]);
    }
    const nodeUrls = Array.from(
      nodeIds,
      (id) => `/.svelte-kit/generated/client/nodes/${id}.js`,
    );
    await Promise.allSettled([
      cacheDevModule(shell, "/.svelte-kit/generated/client/matchers.js"),
      cacheDevModule(shell, "/.svelte-kit/generated/root.js"),
      cacheDevModule(shell, "/.svelte-kit/generated/root.svelte"),
      ...nodeUrls.map((url) => cacheDevModule(shell, url)),
    ]);

    // Direct imports of the node chunks (route modules and error pages).
    const directImports = new Set<string>();
    for (const url of nodeUrls) {
      const cached = await shell.match(url);
      if (!cached) continue;
      const text = await cached.text();
      for (const match of text.matchAll(
        /["'](\/(?:src|@fs|@id|node_modules)\/[^"']*)["']/g,
      )) {
        directImports.add(match[1]);
      }
    }
    await Promise.allSettled(
      Array.from(directImports, (url) => cacheDevModule(shell, url)),
    );
  } catch {
    // Dev precache is best-effort — never fail install.
  }
}

self.addEventListener("install", (event) => {
  // One 404 must not kill the whole install — allSettled per asset.
  event.waitUntil(
    (async () => {
      const shell = await caches.open(SHELL);
      await Promise.allSettled(ASSETS.map((asset) => shell.add(asset)));
      if (DEV) await precacheDevClientModules(shell);
    })(),
  );
  // Take control of open pages so the new version activates immediately.
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      // Keep the current caches (in prod that is SHELL; PAGES/IMAGES are
      // created lazily) and drop everything else — in dev this clears the
      // legacy versioned names once, then persists the stable dev caches
      // across restarts.
      for (const key of await caches.keys()) {
        if (!KEEP.includes(key)) await caches.delete(key);
      }
      await clients.claim();
      // Tell open pages a new version took over (they show a reload toast).
      const clientList = await clients.matchAll({ type: "window" });
      clientList.forEach((client) => {
        client.postMessage({ type: "kissaten:update" });
      });
    })(),
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Handle PWA share target POST requests
	if (event.request.method === 'POST' && url.pathname === '/search') {
		console.log('[SW] Intercepted POST to /search');
		event.respondWith((async () => {
			try {
				const formData = await event.request.formData();
				const imageFile = formData.get('image');
				console.log('[SW] Got image file:', imageFile?.name, imageFile?.size);

				if (imageFile instanceof File && imageFile.size > 0) {
					console.log('[SW] Starting image resize...');
					// Resize image client-side
					const resizedBlob = await resizeImage(imageFile, 1500, 1500);
					console.log('[SW] Resized image, new size:', resizedBlob.size);

					// Store resized image in IndexedDB
					const imageKey = `shared-image-${Date.now()}`;
					await storeImageInDB(resizedBlob, imageKey);
					console.log('[SW] Stored image in IndexedDB with key:', imageKey);

					// Redirect to search page with reference to stored image
					const redirectUrl = `${url.origin}/search?shared-image=${encodeURIComponent(imageKey)}`;
					console.log('[SW] Redirecting to:', redirectUrl);
					return Response.redirect(redirectUrl, 303);
				}
			} catch (error) {
				console.error('[SW] Error processing shared image:', error);
			}

			// Fallback: let the request through to the server
			console.log('[SW] Falling back to server handling');
			return fetch(event.request);
		})());
		return;
	}

  // ignore other POST requests
  if (event.request.method !== "GET") return;

  // Ignore chrome-extension and other non-http(s) schemes
  if (!url.protocol.startsWith("http")) {
    return;
  }

  event.respondWith(
    respond().catch(
      () =>
        new Response("Network error", {
          status: 408,
          headers: { "Content-Type": "text/plain" },
        }),
    ),
  );

  async function respond() {
    // c. Navigations — network-first, stored into PAGES, falling back to the
    // cached exact URL, the cached `/` app shell, or the inline offline page.
    // Never the bare 408 for navigations.
    if (event.request.mode === "navigate") {
      try {
        const response = await fetch(event.request);
        if (response.status === 200 && url.protocol.startsWith("http")) {
          try {
            await caches
              .open(PAGES)
              .then((c) => c.put(event.request, response.clone()));
          } catch {
            // caching failure shouldn't hurt the user
          }
        }
        return response;
      } catch {
        const cached = await caches.match(event.request, { cacheName: PAGES });
        if (cached) return cached;
        const shell = await caches.match("/", { cacheName: PAGES });
        if (shell) return shell;
        return new Response(OFFLINE_HTML, {
          status: 200,
          headers: { "Content-Type": "text/html; charset=utf-8" },
        });
      }
    }

    // d. Images — cache-first; opaque (no-cors cross-origin) and 200 responses
    // are cached with an LRU marker. Fetch failures return the bare 408 (the
    // client `onerror` handlers deal with it).
    if (
      url.pathname.startsWith("/static/data/") ||
      url.pathname.startsWith("/cdn-cgi/") ||
      event.request.destination === "image"
    ) {
      const imageCache = await caches.open(IMAGES);
      const hit = await imageCache.match(event.request);
      if (hit) return hit;

      try {
        const response = await fetch(event.request);
        if (response.type === "opaque" || response.status === 200) {
          try {
            await imageCache.put(event.request, response.clone());
            const metaUrl = new URL("__img-meta" + url.pathname, url).href;
            await imageCache.put(
              metaUrl,
              new Response(JSON.stringify({ t: Date.now() }), {
                headers: { "Content-Type": "application/json" },
              }),
            );
          } catch {
            // put can fail (quota) — still serve the image
          }
          void maybeEvictImages();
        }
        return response;
      } catch {
        return new Response("Network error", {
          status: 408,
          headers: { "Content-Type": "text/plain" },
        });
      }
    }

    // e. API GETs — stale-while-revalidate with TTL (second layer under Dexie).
    if (url.pathname.startsWith("/api/")) {
      const apiCache = await caches.open(PAGES);
      const metaUrl = new URL("__api-meta" + url.pathname + url.search, url)
        .href;
      const metaRes = await apiCache.match(metaUrl);
      if (metaRes) {
        try {
          const meta = (await metaRes.json()) as { t?: number };
          if (typeof meta.t === "number" && Date.now() - meta.t < apiTtl(url)) {
            const fresh = await apiCache.match(event.request);
            if (fresh) return fresh;
          }
        } catch {
          // unreadable meta — treat as stale and refresh below
        }
      }

      try {
        const response = await fetch(event.request);
        if (response.status === 200 && url.protocol.startsWith("http")) {
          try {
            await apiCache.put(event.request, response.clone());
            await apiCache.put(
              metaUrl,
              new Response(JSON.stringify({ t: Date.now() }), {
                headers: { "Content-Type": "application/json" },
              }),
            );
          } catch {
            // caching is best-effort
          }
        }
        return response;
      } catch {
        const stale = await apiCache.match(event.request);
        if (stale) return stale;
        return new Response(
          JSON.stringify({ success: false, error: "offline", data: null }),
          {
            status: 503,
            headers: { "Content-Type": "application/json" },
          },
        );
      }
    }

    // h. `__data.json` — SvelteKit's client-side navigation data. Network-first,
    // stored into PAGES keyed by PATHNAME ONLY: the client appends changing
    // query params (`invalidation=...`, `trailing_slash=1`) to every
    // `__data.json` URL, so keying on the full request would miss the cache
    // on every navigation and break offline visits to previously-seen routes.
    // Offline with nothing cached, serve a synthetic empty
    // `{ type: 'data', nodes: [], uses: {} }` payload (200) so the client
    // re-runs universal loads against the Dexie cache wrapper instead of
    // failing with the DEV "Preloading data ... failed: Internal Error"
    // warning. This branch never returns the bare 408 for data.
    if (url.pathname.endsWith("/__data.json")) {
      const cacheKey = new Request(url.origin + url.pathname);
      try {
        const response = await fetch(event.request);
        if (response.status === 200) {
          try {
            await (await caches.open(PAGES)).put(cacheKey, response.clone());
          } catch {
            // caching is best-effort
          }
        }
        return response;
      } catch {
        const cached = await (await caches.open(PAGES)).match(cacheKey);
        if (cached) return cached;
        return new Response(
          JSON.stringify({ type: "data", nodes: [], uses: {} }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }
    }

    // f. Precache assets (build chunks, fonts, icons, manifest.json) — SHELL.
    if (ASSETS.includes(url.pathname)) {
      const cached = await caches
        .open(SHELL)
        .then((c) => c.match(url.pathname));
      if (cached) return cached;
      // Not found in precache (shouldn't happen) — fall through to generic.
    }

    // g. Generic GETs (no longer reached by `__data.json` — branch h above
    //    intercepts those first): network-first, 200 → PAGES. On failure, dev
    //    module URLs fall back to the install precache by PATHNAME (their
    //    `?t=` queries differ between fetches), then the exact-URL PAGES
    //    lookup, else the bare 408.
    try {
      const response = await fetch(event.request);
      if (response.status === 200 && url.protocol.startsWith("http")) {
        try {
          await caches
            .open(PAGES)
            .then((c) => c.put(event.request, response.clone()));
        } catch {
          // best-effort
        }
      }
      return response;
    } catch {
      if (DEV && DEV_MODULE_PATH.test(url.pathname)) {
        const precached = await caches
          .open(SHELL)
          .then((c) => c.match(url.pathname));
        if (precached) return precached;
      }
      const cached = await caches.match(event.request, { cacheName: PAGES });
      if (cached) return cached;
      return new Response("Network error", {
        status: 408,
        headers: { "Content-Type": "text/plain" },
      });
    }
  }
});
