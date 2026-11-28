---
type: "Operations"
title: "Page Cache Archive & Admin Viewer"
description: "How every scraped page is archived as a self-contained tar.gz (local, append-only, mirrored to private Cloudflare R2) and inspected through the admin-only viewer that compares the cached page with the structured bean."
---

# Page Cache Archive & Admin Viewer

## Overview

Every page a scraper fetches is archived verbatim as a self-contained tarball
under the local cache tree:

```
data/cache/roasters/<roaster_dir>/<YYYYMMDD>/<filename>.tar.gz
```

Each archive contains `metadata.json` (source URL, `cached_at`, roaster,
session id, content length, `has_screenshot`), `page.html` (the raw response
body), and optionally `screenshot.png` when the scraper drove a browser.

The archive is the **audit trail for structured bean data**: when a bean looks
wrong in the admin UI, a reviewer can open the exact HTML (and screenshot) the
scraper saw and compare it with the extracted `CoffeeBean`. It is local-first,
append-only (a new scrape session gets a new date directory; nothing is
rewritten), and mirrored to a **private Cloudflare R2 bucket** so an API host
without the scraper's disk can still serve the viewer.

The feature landed in commit `20543a6`; the canonical operational reference is
[`docs/CACHE_ARCHIVE.md`](../../docs/CACHE_ARCHIVE.md).

## Flow

```
scraper BaseScraper._save_page_cache
        │  writes
        ▼
data/cache/roasters/<roaster_dir>/<YYYYMMDD>/<filename>.tar.gz
        │  kissaten cache-sync  (rclone copy --immutable)
        ▼
R2: <prefix>/roasters/<roaster_dir>/<YYYYMMDD>/<filename>.tar.gz
        │  read layer: local first, R2 fallback
        ▼
FastAPI admin endpoints  (/v1/admin/cache/...)
        │  X-Kissaten-Admin-Token
        ▼
SvelteKit admin viewer  (AdminCachedPageViewer.svelte)
```

## Deterministic filenames

`src/kissaten/cache/page_cache.py:page_cache_filename()` derives the archive
name from the product URL:

1. Take the last non-empty path segment.
2. Strip a trailing `.html` / `.php`.
3. Lowercase.
4. Replace every character outside `[a-z0-9_-]` with `_`.
5. Append `.tar.gz`.

URLs with no path fall back to the first 8 hex characters of `md5(url)`.

Because the same URL always maps to the same key within a session date:

- uploads are idempotent and safe to retry;
- **no manifest or index file is needed** — the object key is the index;
- multiple hosts uploading the same page write the same key.

There is no global index; listing is always scoped to a **per-roaster prefix**.
`BaseScraper._get_cache_filename()` delegates straight to
`page_cache_filename()`, and `tests/unit/test_page_cache.py` pins the parity so
the scraper write path and the viewer read path cannot drift.

## Roaster directory resolution

The viewer must find the cache directory even when it does not know how the
scraper spelled it. `_candidate_roaster_dirs()` in
`src/kissaten/api/cache_viewer.py` builds an ordered, de-duplicated list:

1. The registry's `ScraperInfo.directory_name` for a matching
   `roaster_name` (best effort; lookup failures are logged and skipped).
2. `slugify_roaster(roaster_name)` from `src/kissaten/api/utils.py`.
3. The first segment of the bean's `bean_url_path`.

Every candidate is tried for both local listings and R2 listings.

### The Kafferäven case

This is why the URL-path fallback exists. The registry `roaster_name` is
`Kafferäven`, so `ScraperInfo.directory_name` and `slugify_roaster()` both
replace the `ä` with `_` and produce **`kaffer_ven`**. But the scraper overrides
`_get_roaster_dir_name()` to return **`kafferaven`**, matching its historical
`data/roasters/` directory and URL slug. The cache tree historically contains
both names. The viewer's candidate list therefore resolves to `kaffer_ven` and
then `kafferaven` (from `bean_url_path`), and scans both — neither the registry
nor `slugify_roaster` alone would find the archives written under
`kafferaven`.

## Source map

| Path | Responsibility |
|---|---|
| `src/kissaten/cache/page_cache.py` | Filename convention, `CacheSnapshot`, local listing/read, safe tar extraction, `<base href>` injection |
| `src/kissaten/cache/r2_page_cache.py` | Optional read-only R2 listing/download, in-memory TTL listing cache, 25 MB object cap |
| `src/kissaten/api/cache_viewer.py` | Admin-only FastAPI router: bean lookup, roaster-dir candidates, local/R2 merge, content endpoints |
| `src/kissaten/scrapers/base.py` | `_save_page_cache()` writes the tarball; `_get_cache_filename()` delegates to `page_cache_filename()` |
| `src/kissaten/cli/main.py` (`cache_sync`) | `kissaten cache-sync`: builds `rclone copy --immutable`, optional `--verify` |
| `frontend/src/lib/api/cache.remote.ts` | Admin-gated server `query` that calls the FastAPI list endpoint |
| `frontend/src/lib/components/admin/AdminCachedPageViewer.svelte` | Snapshot dialog with Screenshot / Rendered page / Metadata / Raw archive tabs |
| `frontend/src/lib/components/admin/AdminCacheInspectorSection.svelte` | Standalone Cache inspector on `/admin` (path or roaster+bean slugs) |
| `frontend/src/routes/(main)/admin/cache/content/+server.ts` | Same-origin admin proxy that re-checks the session and injects the token server-side |
| `tests/unit/test_page_cache.py` | Filename parity, traversal rejection, tar extraction, base-href injection |
| `tests/unit/test_cache_sync.py` | `copy` (not `sync`), `--immutable`, one-way verify, env-based credentials, roaster scoping |
| `tests/test_cache_viewer_api.py` | Auth (401/503), list/content responses, security headers, snapshot-belongs-to-bean checks |

## Syncing to R2

```bash
kissaten cache-sync [--roaster <name>] [--verify]
```

`cache-sync` resolves the local source (default `data/cache/roasters`) and
destination `<prefix>/roasters[/<name>]`, then runs:

```
rclone copy <source> kissatenr2:<bucket>/<prefix>/roasters --immutable ...
```

The command **always uses `rclone copy`, never `sync`, and never passes
`--delete`**. The archive is additive only:

- A host that has only *new* files cannot delete remote objects — `copy` never
  removes files that exist only at the destination.
- `--verify` runs `rclone check --one-way --size-only` after the copy. It is
  one-way: it exits non-zero when a local archive is missing from R2, but does
  **not** check for R2 objects that are absent locally.
- `--roaster <name>` scopes both source and destination to a single segment
  (validated against `.`, `..`, and separators) so a large tree is not
  re-walked.
- `--dry-run` previews the upload; credentials travel in `RCLONE_CONFIG_*`
  environment variables, never in the process argv.

**Immutable-conflict failure mode**: `--immutable` treats existing remote
objects as immutable. If a local file maps to a key that already exists with
*different bytes*, rclone reports the conflict and errors instead of
overwriting it. This is intentional — the bucket is a historical record, so
same-key/different-bytes is a signal to investigate, not to clobber.

## R2 configuration

| Variable | Purpose |
|---|---|
| `KISSATEN_R2_ENDPOINT` | S3 endpoint, `https://<account_id>.r2.cloudflarestorage.com` |
| `KISSATEN_R2_BUCKET` | Bucket name (the CLI defaults to `kissaten`) |
| `KISSATEN_R2_PREFIX` | Key prefix, default `cache` |
| `KISSATEN_R2_ACCESS_KEY_ID` | R2 access key id |
| `KISSATEN_R2_SECRET_ACCESS_KEY` | Matching secret |
| `KISSATEN_R2_LIST_CACHE_TTL` | Optional listing-cache TTL in seconds (default `300`) |
| `KISSATEN_CACHE_DIR` | Local cache root, default `data/cache` |

The bucket stays **private** — no public bucket or public object URLs. Use two
tokens: a **read/write** token on the scraper host that runs `cache-sync` and
the scrapers, and a **separate read-only** token (`GetObject` + `ListBucket`)
on the API server. `r2_page_cache.r2_available()` is true only when the
endpoint, bucket, access key, and secret are all set.

## Read path

The read layer is local-first with an optional R2 fallback:

- **Listing** (`_gather_snapshots`): local snapshots are listed first, R2
  snapshots are merged in, and **local wins on conflict** (same
  `session_date` + `filename`).
- **Content** (`_read_raw_snapshot`): every candidate roaster directory is
  tried locally, then every candidate is tried in R2. A missing or unreadable
  local file falls through to R2.
- **R2 listing** uses a boto3 `list_objects_v2` paginator scoped to one
  roaster prefix and caches the result in-process for a short TTL
  (`KISSATEN_R2_LIST_CACHE_TTL`, default 300s) because the viewer is often
  reopened.
- **25 MB cap** (`MAX_OBJECT_SIZE`): archives larger than this are refused,
  both by `ContentLength` and after download.
- The R2 path is entirely optional. An API host with **no local `data/cache/`
  tree and no R2 credentials** still starts and serves empty results; with R2
  configured it needs no local disk at all.

## API

Both endpoints live under the `cache_viewer` router and are read-only.

### `GET /v1/admin/cache/beans/{roaster_slug}/{bean_slug}`

Lists the cached snapshots for a bean. The response carries the bean summary,
the candidate `roaster_dirs`, the merged snapshots (source `local`/`r2`, size,
last modified, `has_screenshot`), which backends are available (`storage`), and
`warnings`.

### `GET /v1/admin/cache/beans/{roaster_slug}/{bean_slug}/content`

Serves one snapshot's content:

| Query | Value |
|---|---|
| `session` | Snapshot session date (`YYYYMMDD`) |
| `filename` | Cache archive filename (`*.tar.gz`) |
| `kind` | `html` \| `screenshot` \| `metadata` \| `raw` |

`html` returns the archived page with an injected `<base href>`; `screenshot`
returns the PNG; `metadata` returns `metadata.json`; `raw` returns the gzip
archive as an attachment.

### Auth and ownership

- Every request needs `X-Kissaten-Admin-Token`, compared in constant time with
  `KISSATEN_ADMIN_API_TOKEN`.
- The token is read at request time. If the environment variable is **unset**,
  the endpoint returns **503** ("not configured"); a wrong or missing header
  returns **401**.
- The content endpoint recomputes the bean's filename from its URL and requires
  `(session, filename)` to be one of *that bean's* available snapshots.
  Malformed `session`/`filename` return **400**; an unrelated or unknown
  snapshot returns **404**. A bean cannot be used to read another bean's
  archive.
- The router does not apply the public `requires_review` filter: admins must be
  able to inspect pending products too.

## Security

The archive is untrusted third-party HTML, so it is locked down at both layers.

**FastAPI** (`cache_viewer.py`):

- HTML is served with `Content-Security-Policy: sandbox; default-src 'none';
  script-src 'none'; img-src https: http: data:; style-src https: http:
  'unsafe-inline'; font-src https: http: data:; base-uri https: http:;
  form-action 'none'`.
- `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`,
  `Cache-Control: private, no-store`.
- Tarballs are read member-by-member (never `extractall`), so archive paths
  cannot touch the filesystem. Local resolution rejects `..`, absolute paths,
  and symlink escapes.

**SvelteKit** (`cache.remote.ts`, `admin/cache/content/+server.ts`):

- `requireAdmin()` throws 401/403 unless `locals.user.role === "admin"`.
- The shared token is only ever sent server-to-server; it **never reaches the
  browser**.
- The content proxy re-validates every query parameter and builds a fresh
  header set (never forwards upstream `Set-Cookie`/CORS), then applies the same
  hardening headers.
- The viewer renders the page in an iframe with `sandbox=""` (fully sandboxed;
  scripts disabled).

## Admin UI

`AdminCachedPageViewer.svelte` is the shared dialog. It is opened from three
entry points:

- **Review queue** — a "View cache" action on a bean in the tasting-kit review
  queue (`AdminReviewQueueSection.svelte`).
- **Not-a-bean reports** — a "View cache" action on a reported product
  (`AdminNotABeanReportsSection.svelte`).
- **Standalone Cache inspector** on `/admin` (`AdminCacheInspectorSection.svelte`),
  which accepts a bean path such as `/kaffer_ven/ethiopia-guji` (or separate
  roaster and bean slugs) for any bean, even one outside a review queue.

The dialog offers a snapshot selector (session date, `local`/`r2` source, size,
last modified), storage badges, a "Copy cache path" action, an "Open live
source" link, and four tabs: **Screenshot**, **Rendered page**, **Metadata**,
and **Raw archive**.

## Known limitations

- **`has_screenshot` is `null` in listings.** Determining it requires opening
  the archive, so listings leave it `None`. The viewer optimistically requests
  the screenshot and falls back to the "No screenshot" message on load error.
- **JSON-only Shopify scrapers may have no page archive.** A scraper that runs
  with `scrape_product_pages=False` never fetches product HTML, so there is
  nothing to cache and the viewer shows "No cached page for this bean".
- **URL-to-filename matching can miss renamed or redirected products.** The
  viewer derives the filename from the bean's *current* `url`; an archive
  stored under an older URL will not be found.
- **No manifest.** R2 listings are a per-roaster `ListObjectsV2` (paginated),
  amortised by the in-process TTL cache rather than a global index.

## Worked example

`poma_coffee` has a bean JSON at
`data/roasters/poma_coffee/20260803/la_leona_-_ef2_papayo_180208.json` and a
matching archive at
`data/cache/roasters/poma_coffee/20260803/la-leona-ef2-papayo.tar.gz`. Opening
the cached page shows a Shopify **"Access denied"** page (the HTML contains the
access-denied/captcha markers), which explains the near-empty bean JSON: the
extractor had almost nothing structured to read. To upload this roaster and
confirm every local archive reached R2:

```bash
kissaten cache-sync --roaster poma_coffee --verify
```

## Storage and cost

At the time of writing the archive is roughly **48 GB**. Cloudflare R2 Standard
storage is billed only after a 10 GB free tier at about $0.015/GB-month, so
~38 GB billable is roughly **$0.57/month**. Egress from R2 is free. Keep all
objects — the archive is the historical record and storage is cheap relative to
re-scraping.

## Related

- [`docs/CACHE_ARCHIVE.md`](../../docs/CACHE_ARCHIVE.md) — canonical
  operational reference (layout, rclone config, environment variables).
- [`AGENTS.md`](../../AGENTS.md) — project invariants, including the cache
  archive and lock.
- [Scraping System](../scrapers/scraping-system.md) — `BaseScraper`,
  `_save_page_cache`, scraper output.
- [Backend API & Database](../api/backend-api.md) — sub-routers and the admin
  cache endpoints.
- [Operations](operations.md) — CLI, scheduling, validation, deployment.
