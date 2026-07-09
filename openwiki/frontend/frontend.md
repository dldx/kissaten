# Frontend

## Overview

The frontend is a SvelteKit 5 application (runes mode) using shadcn-svelte UI components, Tailwind CSS v4, TypeScript, and Bun as the package manager. It provides a modern, responsive interface for discovering and exploring coffee beans.

## Route Structure

```
frontend/src/routes/
├── (main)/                    # Primary layout group
│   ├── +page.svelte           # Home page (hero, search, featured roasters)
│   ├── search/                # Advanced search with faceted filters
│   ├── roasters/
│   │   ├── +page.svelte       # All roasters listing
│   │   └── [roaster_name]/    # Roaster profile + beans
│   │       └── [bean_name]/   # Bean detail page
│   ├── origins/               # Geographic origin browser
│   ├── flavours/              # Tasting note / flavour explorer
│   ├── processes/             # Processing method pages
│   ├── varietals/             # Varietal pages
│   ├── analytics/             # Analytics dashboard
│   ├── brew-assistant/        # AI brew recipe generator (beta-gated)
│   ├── vault/
│   │   ├── collection/        # User's bean collection
│   │   ├── saved/             # Saved beans
│   │   └── recently-viewed/   # Recently viewed beans
│   └── stickers/              # Sticker page
├── (no-layout)/               # Standalone pages (no main layout)
├── auth/                      # Authentication (magic-link email via better-auth)
├── og/                        # Open Graph image generation
├── sitemap.xml/               # Main sitemap
├── sitemap-origins.xml/       # Origins sitemap
├── sitemap-processes.xml/     # Processes sitemap
├── sitemap-varietals.xml/     # Varietals sitemap
└── sitemap-static.xml/        # Static pages sitemap
```

## API Client (`frontend/src/lib/api.ts`)

Central TypeScript API client (~53K lines) that handles all backend communication. Modular remote APIs are under `frontend/src/lib/api/` (e.g., `custom_beans.remote.ts` for user-created beans).

## Key Features

### Tasting Wizard (`frontend/src/lib/tasting/` + `components/tasting/TastingWizard.svelte`)
- Guided coffee tasting experience with drag-and-drop note ordering
- Bean search combobox for selecting the bean being tasted
- Add bean form for beans not in the database
- Save/unsave beans to vault from the wizard

### Brew Assistant (`frontend/src/routes/(main)/brew-assistant/+page.svelte`)
- Beta-gated AI-powered recipe generator
- Sends bean attributes and user equipment to `POST /v1/brew-assistant/recipe`
- Returns personalized pour-over/espresso recipes

### Vault
- User's saved beans, collection, and recently-viewed beans
- Bean card actions: save/unsave, share to BeanConqueror
- Saved beans are synced via full reconciliation (see [sync system](sync-system.md))

### Sync System (`frontend/src/lib/sync/`)

The frontend uses a **local-first sync architecture**: Dexie (IndexedDB) stores all user data locally for offline use, with bidirectional sync to a remote Turso/libSQL database via Drizzle ORM and SvelteKit server endpoints.

**Four synced data types:**
- **Tasting sessions** — push/pull with `since` cursor, last-write-wins
- **Custom beans** — push/pull with `since` cursor, batch push (50/batch)
- **Saved beans** — push via individual save/unsave/notes commands + full reconciliation pull
- **Brew recipes** — push/pull with `since` cursor, only `isSaved` recipes are synced

**Key features:**
- Three sync modes: `normal` (incremental), `verify-then-fix` (count+digest check then targeted repair), `force-full` (re-fetch everything)
- SHA-256 digest-based consistency verification that catches content drift without downloading full payloads
- Offline-first: reads always come from Dexie; writes go to Dexie immediately with `syncedAt = null`; sync retries on next cycle
- Guest-to-user claiming: unowned local records are assigned to the logged-in user on first sync
- Reactive Svelte 5 runes trigger UI updates via `dbUpdateTrigger` counters

For full architecture details, protocol, schema evolution, conflict resolution, and change guidance, see **[sync-system.md](sync-system.md)**.

### State Management (`frontend/src/lib/stores/`)
- Svelte stores for theme, search state, user session, etc.

### Authentication
- Magic-link email auth via `better-auth`
- `frontend/src/lib/auth-client.ts` — Auth client
- `frontend/src/routes/auth/` — Auth routes
- Server-side hooks in `hooks.server.ts` handle session middleware

### BeanConqueror Share
- `BeanConquerorShareButton.svelte` — Generates a share link that opens the BeanConqueror app with pre-filled bean data
- Uses protobuf-encoded, base64-chunked URL parameters

### Cloudflare Images
- `frontend/src/lib/utils/cfImage.ts` — Utility for generating Cloudflare Images CDN URLs for resized product images
- `ResponsiveImage.svelte` — Responsive image component using CF Images

### SEO
- Sitemap routes for origins, processes, varietals, and static pages
- `frontend/src/lib/seo.ts` — SEO metadata utilities
- Open Graph image generation at `/og/`

### PWA
- `frontend/src/service-worker.ts` — Service worker for PWA support
- `frontend/src/lib/pwa-install.svelte.ts` — PWA install prompt

## Components (`frontend/src/lib/components/`)

Key components:
- `CoffeeBeanCard.svelte` — Bean card with image, name, roaster, tasting notes
- `bean/BeanCardActions.svelte` — Action buttons (save, share, etc.)
- `bean/BeanConquerorShareButton.svelte` — BeanConqueror share button
- `tasting/TastingWizard.svelte` — Full tasting wizard
- `tasting/AddBeanForm.svelte` — Add custom bean form
- `tasting/BeanSearchCombobox.svelte` — Bean search combobox
- `vault/SaveBeanButton.svelte` — Save/unsave bean to vault
- `FlavourProfileDonut.svelte` — 3D flavour visualization (Threlte/Three.js)
- `RoastProfileBar.svelte` — Roast profile visualization
- `CurrencySelector.svelte` — Currency selector
- `ResponsiveImage.svelte` — Responsive CF Images component

## Server Hooks

- `hooks.server.ts` — Sentry initialization, auth session middleware, request logging
- `hooks.client.ts` — Client-side Sentry, theme initialization
- `instrumentation.server.ts` — Sentry server instrumentation

## Configuration

- `svelte.config.js` — SvelteKit configuration (adapter, preprocessing)
- `vite.config.ts` — Vite build configuration
- `package.json` — Dependencies (SvelteKit, shadcn-svelte, Tailwind, Threlte, better-auth, Dexie, Drizzle, etc.)
- `app.html` — HTML template
- `app.css` — Global styles (Tailwind)
