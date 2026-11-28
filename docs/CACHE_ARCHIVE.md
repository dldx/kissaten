# Page Cache Archive (local + Cloudflare R2)

Kissaten keeps a raw snapshot of every page a scraper fetches. Those snapshots
are the audit trail for structured bean data: when a bean looks wrong in the
admin UI, a reviewer can open the exact HTML (and optional screenshot) the
scraper saw. The local archive is append-only and is mirrored to a private
Cloudflare R2 bucket so a server without the scraper's disk can still serve
the viewer.

## What the page cache is

`BaseScraper._save_page_cache` writes one self-contained tarball per fetched
page:

```
data/cache/roasters/<roaster_dir>/<YYYYMMDD>/<filename>.tar.gz
```

- `<roaster_dir>` is the roaster's directory name (same as under
  `data/roasters/`).
- `<YYYYMMDD>` is the scraping session date (UTC).
- Each tarball contains `metadata.json` (source URL, `cached_at`, roaster,
  session id, content length, whether a screenshot exists), `page.html` (the
  raw response body), and optionally `screenshot.png` when the scraper uses a
  browser.

Nothing in the cache is deduplicated or rewritten after the fact; a new
scrape session gets a new date directory.

## Why filenames are deterministic

The archive filename is derived from the last path segment of the product URL,
lowercased, with `.html` / `.php` stripped and every character outside
`[a-z0-9_-]` replaced by `_`, followed by `.tar.gz`. That means the same
product URL always maps to the same key (within a session date), so:

- Uploads are idempotent and can be retried safely.
- No manifest or index file is needed — the object key is the index.
- Multiple hosts uploading the same page write the same key.

## R2 layout

The bucket mirrors the local tree under the configured prefix:

```
<prefix>/roasters/<roaster_dir>/<YYYYMMDD>/<filename>.tar.gz
```

With the defaults (`KISSATEN_R2_PREFIX=cache`) that is:

```
cache/roasters/...
```

## R2 token setup

- Create a private R2 bucket (e.g. `kissaten`). No public bucket or custom
  domain is needed.
- Create a **read/write** R2 API token for the scraper host that runs
  `kissaten cache-sync` and the scrapers.
- Create a **separate read-only** token for the API server. The admin cache
  viewer only needs `GetObject` and `ListBucket`.
- Store the values in the environment (see `env.example`); never commit them.

Both tokens use the same S3 endpoint
`https://<account_id>.r2.cloudflarestorage.com`.

## rclone remote configuration

`kissaten cache-sync` does not require a persistent rclone remote: it passes
the configuration through `RCLONE_CONFIG_*` environment variables (see
below). For manual/rclone-only use you can create a normal remote:

```ini
[r2]
type = s3
provider = Cloudflare
access_key_id = ...
secret_access_key = ...
endpoint = https://<account_id>.r2.cloudflarestorage.com
region = auto
```

Store it in `~/.config/rclone/rclone.conf` (or use
`rclone config --config <path>`). The CLI's temporary remote is named
`kissatenr2`.

## Manual sync via the CLI

Preview first, then copy, then verify:

```bash
kissaten cache-sync --dry-run
kissaten cache-sync
kissaten cache-sync --verify
```

To sync a single roaster instead of the whole (multi-gigabyte) tree, pass
`--roaster`. It resolves `<source-dir>/<roaster>` and uploads it to
`<bucket>/<prefix>/roasters/<roaster>`, preserving the roaster directory
name. `--verify` checks the same scoped source and destination:

```bash
kissaten cache-sync --roaster poma_coffee --verify
```

`--roaster` must be a single path segment (non-empty, no `/` or `\`, not `.`
or `..`), and the roaster directory must exist under `--source-dir`.

Useful options:

- `--source-dir` (default `data/cache/roasters`)
- `--roaster <name>` (optional; sync only `<source-dir>/<name>` to
  `<bucket>/<prefix>/roasters/<name>`)
- `--bucket`, `--prefix`, `--endpoint`, `--access-key-id`,
  `--secret-access-key` (each falls back to its `KISSATEN_R2_*` env var)
- `--transfers` (default 16), `--checkers` (default 32)
- `--no-progress`, `--verbose`
- `--verify` runs `rclone check --one-way --size-only` after the copy and
  exits non-zero if any local archive is missing from R2.

The command always uses `rclone copy`, never `sync`, and never passes
`--delete`. `--immutable` makes rclone skip remote objects that already exist
instead of trying to overwrite them. Files that exist only on the remote are
left alone.

## Raw rclone equivalent

```bash
rclone copy data/cache/roasters kissatenr2:kissaten/cache/roasters \
  --fast-list --immutable --stats 30s --transfers 16 --checkers 32 --progress
```

The rule is: **`rclone copy --immutable`, never `rclone sync --delete`.**
`sync` would delete remote objects that are absent locally (for example after
a host prunes its disk), which destroys the archive.

The CLI's environment-based remote is equivalent to this rclone config:

```bash
RCLONE_CONFIG_KISSATENR2_TYPE=s3 \
RCLONE_CONFIG_KISSATENR2_PROVIDER=Cloudflare \
RCLONE_CONFIG_KISSATENR2_ACCESS_KEY_ID=... \
RCLONE_CONFIG_KISSATENR2_SECRET_ACCESS_KEY=... \
RCLONE_CONFIG_KISSATENR2_ENDPOINT=https://<account_id>.r2.cloudflarestorage.com \
RCLONE_CONFIG_KISSATENR2_REGION=auto \
rclone copy data/cache/roasters kissatenr2:kissaten/cache/roasters --immutable
```

This keeps secrets out of the process argv (and therefore out of `ps` output
and shell history).

## Multi-host uploads

Every scraper host can upload to the same prefix. Because nothing is ever
deleted and overlapping keys are skipped under `--immutable`, hosts cannot
clobber each other's archives. It is safe (and intended) to run `cache-sync`
on every host.

## Server without a local cache

An API server that does not scrape has no local `data/cache/` tree. The
admin viewer lists a single roaster prefix in R2 on demand (cached in-process
for a short TTL) and downloads individual archives when opened. When both a
local file and an R2 object exist, the local file wins. The R2 path is
entirely optional: if the `KISSATEN_R2_*` variables are unset, only local
archives are served.

## Storage and cost

At the time of writing the archive is roughly **48 GB**. Cloudflare R2
Standard storage is billed after a 10 GB free tier at about $0.015/GB-month,
so ~38 GB billable is roughly **$0.57/month**. Egress from R2 is free. Keep
all objects — the archive is the historical record and storage is cheap
relative to re-scraping.

## Security

The archive contains third-party HTML from roaster sites. Treat it as
untrusted:

- The cache viewer API is **admin-only**, gated by
  `KISSATEN_ADMIN_API_TOKEN` (sent as `X-Kissaten-Admin-Token`).
- HTML is served with a restrictive Content-Security-Policy and rendered in
  a sandboxed iframe with scripts disabled.
- The R2 bucket stays private; no public bucket or public object URLs.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `KISSATEN_CACHE_DIR` | Local cache root (default `data/cache`). |
| `KISSATEN_R2_ENDPOINT` | R2 S3 endpoint, `https://<account_id>.r2.cloudflarestorage.com`. |
| `KISSATEN_R2_BUCKET` | Bucket name (default `kissaten` for the CLI). |
| `KISSATEN_R2_PREFIX` | Key prefix (default `cache`). |
| `KISSATEN_R2_ACCESS_KEY_ID` | R2 access key id (read/write on scraper hosts, read-only on the API server). |
| `KISSATEN_R2_SECRET_ACCESS_KEY` | Matching R2 secret key. |
| `KISSATEN_ADMIN_API_TOKEN` | Shared secret for the admin-only cache viewer API. |

See `env.example` for a commented template.
