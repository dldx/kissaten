<script lang="ts">
  import { untrack } from "svelte";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import { Button, buttonVariants } from "$lib/components/ui/button/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { cn } from "$lib/utils";
  import { toast } from "svelte-sonner";
  import DatabaseIcon from "lucide-svelte/icons/database";
  import ImageIcon from "lucide-svelte/icons/image";
  import ImageOffIcon from "lucide-svelte/icons/image-off";
  import ArchiveIcon from "lucide-svelte/icons/archive";
  import ExternalLinkIcon from "lucide-svelte/icons/external-link";
  import CopyIcon from "lucide-svelte/icons/copy";
  import DownloadIcon from "lucide-svelte/icons/download";
  import AlertTriangleIcon from "lucide-svelte/icons/alert-triangle";
  import {
    listCachedSnapshots,
    type CachedSnapshot,
    type CachedSnapshotsData,
  } from "$lib/api/cache.remote";

  interface Props {
    open?: boolean;
    roasterSlug?: string;
    beanSlug?: string;
    beanName?: string;
  }

  let {
    open = $bindable(false),
    roasterSlug = "",
    beanSlug = "",
    beanName = "",
  }: Props = $props();

  type CacheKind = "html" | "screenshot" | "metadata" | "raw";
  type CacheTab = CacheKind;

  const TABS: { id: CacheTab; label: string }[] = [
    { id: "screenshot", label: "Screenshot" },
    { id: "html", label: "Rendered page" },
    { id: "metadata", label: "Metadata" },
    { id: "raw", label: "Raw archive" },
  ];

  let data = $state<CachedSnapshotsData | null>(null);
  let loading = $state(false);
  let loadError = $state("");
  let selectedKey = $state<string | null>(null);
  let activeTab = $state<CacheTab>("html");

  let metadataJson = $state("");
  let metadataLoading = $state(false);
  let metadataError = $state("");
  let screenshotError = $state(false);
  let copiedPath = $state(false);

  let loadKey = $state("");
  let requestId = 0;
  let metadataRequestId = 0;

  function snapshotKey(snapshot: CachedSnapshot): string {
    return `${snapshot.session_date}|${snapshot.filename}`;
  }

  function errorMessage(err: unknown, fallback: string): string {
    if (err instanceof Error && err.message) return err.message;
    if (typeof err === "object" && err !== null) {
      const maybe = err as {
        message?: unknown;
        body?: { message?: unknown };
      };
      if (typeof maybe.message === "string" && maybe.message) {
        return maybe.message;
      }
      if (typeof maybe.body?.message === "string" && maybe.body.message) {
        return maybe.body.message;
      }
    }
    return fallback;
  }

  const displayName = $derived(beanName || data?.bean.name || "");

  const selectedSnapshot = $derived(
    selectedKey === null
      ? null
      : (data?.snapshots.find((s) => snapshotKey(s) === selectedKey) ?? null),
  );
  const canOpenScreenshot = $derived(
    selectedSnapshot?.has_screenshot !== false,
  );
  const screenshotUnavailable = $derived(
    selectedSnapshot?.has_screenshot === false,
  );

  function formatSession(value: string): string {
    return /^\d{8}$/.test(value)
      ? `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6, 8)}`
      : value;
  }

  function formatBytes(bytes: number | null | undefined): string {
    if (bytes === null || bytes === undefined || !Number.isFinite(bytes)) {
      return "—";
    }
    if (bytes <= 0) return "0 B";
    const units = ["B", "KB", "MB", "GB"];
    const exponent = Math.min(
      Math.floor(Math.log(bytes) / Math.log(1024)),
      units.length - 1,
    );
    const value = bytes / 1024 ** exponent;
    return `${value >= 10 || exponent === 0 ? Math.round(value) : value.toFixed(1)} ${units[exponent]}`;
  }

  function formatDate(value: string | null): string {
    if (!value) return "unknown";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString();
  }

  function contentUrl(
    kind: CacheKind,
    snapshot: CachedSnapshot,
    cachebust?: string,
  ): string {
    const params = new URLSearchParams({
      roaster: roasterSlug,
      bean: beanSlug,
      session: snapshot.session_date,
      filename: snapshot.filename,
      kind,
    });
    if (cachebust) params.set("cachebust", cachebust);
    return `/admin/cache/content?${params.toString()}`;
  }

  function resetViewer() {
    requestId += 1;
    metadataRequestId += 1;
    data = null;
    loading = false;
    loadError = "";
    selectedKey = null;
    activeTab = "html";
    metadataJson = "";
    metadataLoading = false;
    metadataError = "";
    screenshotError = false;
    copiedPath = false;
  }

  function selectSnapshot(snapshot: CachedSnapshot) {
    selectedKey = snapshotKey(snapshot);
    metadataJson = "";
    metadataError = "";
    metadataLoading = false;
    metadataRequestId += 1;
    screenshotError = false;
    // Default to the screenshot unless we know this snapshot lacks one; an
    // unknown screenshot state still gets the image, which falls back to the
    // unavailable message if it fails to load.
    activeTab = snapshot.has_screenshot === false ? "html" : "screenshot";
  }

  async function loadSnapshots(roaster: string, bean: string) {
    const id = ++requestId;
    loading = true;
    loadError = "";
    data = null;
    selectedKey = null;
    try {
      const result = await listCachedSnapshots({
        roasterSlug: roaster,
        beanSlug: bean,
      });
      if (id !== requestId) return;
      data = result;
      const first = result.snapshots[0];
      if (first) selectSnapshot(first);
    } catch (err) {
      if (id !== requestId) return;
      loadError = errorMessage(err, "Failed to load cached snapshots.");
    } finally {
      if (id === requestId) loading = false;
    }
  }

  function onSnapshotChange(key: string) {
    const snapshot = data?.snapshots.find((s) => snapshotKey(s) === key);
    if (snapshot) selectSnapshot(snapshot);
  }

  function selectTab(tab: CacheTab) {
    activeTab = tab;
    if (tab === "metadata" && !metadataJson && !metadataLoading) {
      void loadMetadata();
    }
  }

  async function loadMetadata() {
    const snapshot = selectedSnapshot;
    if (!snapshot) return;
    const id = ++metadataRequestId;
    metadataLoading = true;
    metadataError = "";
    metadataJson = "";
    try {
      const res = await fetch(contentUrl("metadata", snapshot), {
        headers: { accept: "application/json" },
      });
      if (!res.ok) {
        throw new Error(`Metadata request failed (HTTP ${res.status}).`);
      }
      const text = await res.text();
      if (id !== metadataRequestId) return;
      try {
        metadataJson = JSON.stringify(JSON.parse(text), null, 2);
      } catch {
        metadataJson = text;
      }
    } catch (err) {
      if (id !== metadataRequestId) return;
      metadataError = errorMessage(err, "Failed to load metadata.");
    } finally {
      if (id === metadataRequestId) metadataLoading = false;
    }
  }

  function cachePath(): string | null {
    const snapshot = selectedSnapshot;
    if (!snapshot || !data) return null;
    const roasterDir = data.roaster_dirs[0] ?? roasterSlug;
    return `data/cache/roasters/${roasterDir}/${snapshot.session_date}/${snapshot.filename}`;
  }

  async function copyCachePath() {
    const path = cachePath();
    if (!path) return;
    try {
      await navigator.clipboard.writeText(path);
      copiedPath = true;
      setTimeout(() => (copiedPath = false), 2000);
      toast.success("Cache path copied.");
    } catch {
      toast.error("Could not copy the cache path.");
    }
  }

  // Load when the dialog opens (or the target bean changes) and fully reset
  // when it closes, so reopening always starts from a clean slate.
  $effect(() => {
    const isOpen = open;
    const roaster = roasterSlug;
    const bean = beanSlug;
    untrack(() => {
      if (!isOpen) {
        if (loadKey !== "") {
          loadKey = "";
          resetViewer();
        }
        return;
      }

      const key = `${roaster}\u0000${bean}`;
      if (key === loadKey) return;
      loadKey = key;
      resetViewer();

      if (!roaster || !bean) {
        loadError = "No bean selected.";
        return;
      }
      void loadSnapshots(roaster, bean);
    });
  });
</script>

<Dialog.Root bind:open>
  <Dialog.Content class="sm:max-w-5xl max-h-[92vh] overflow-y-auto">
    <Dialog.Header>
      <Dialog.Title class="flex items-center gap-2">
        <DatabaseIcon class="w-5 h-5 text-primary" />
        Cached page
      </Dialog.Title>
      <Dialog.Description>
        {#if displayName}
          Raw page snapshots for <span class="font-medium text-foreground"
            >{displayName}</span
          >.
        {:else}
          Raw page snapshots for this bean.
        {/if}
      </Dialog.Description>
    </Dialog.Header>

    {#if loading}
      <div class="py-12 text-muted-foreground text-center text-sm">
        Loading cached snapshots…
      </div>
    {:else if loadError}
      <div
        class="flex items-start gap-2 bg-destructive/10 p-3 border border-destructive/30 rounded-md text-destructive text-sm"
      >
        <AlertTriangleIcon class="mt-0.5 w-4 h-4 shrink-0" />
        <span>{loadError}</span>
      </div>
    {:else if !data || data.snapshots.length === 0}
      <div class="flex flex-col items-center gap-3 py-12 text-center">
        <ArchiveIcon class="w-10 h-10 text-muted-foreground" />
        <p class="font-medium">No cached page for this bean</p>
        <p class="max-w-md text-muted-foreground text-sm">
          No cached page for this bean — it may have been scraped from JSON/API
          without page caching.
        </p>
        {#if data?.warnings?.length}
          <ul class="mt-2 text-muted-foreground text-xs">
            {#each data.warnings as warning (warning)}
              <li>{warning}</li>
            {/each}
          </ul>
        {/if}
      </div>
    {:else}
      <div class="space-y-3">
        <div
          class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"
        >
          <div class="flex flex-col gap-1.5">
            <label class="font-medium text-sm" for="cached-snapshot"
              >Snapshot</label
            >
            <select
              id="cached-snapshot"
              class="h-9 rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
              value={selectedKey ?? ""}
              onchange={(event: Event) =>
                onSnapshotChange(
                  (event.currentTarget as HTMLSelectElement).value,
                )}
            >
              {#each data.snapshots as snapshot (snapshotKey(snapshot))}
                <option value={snapshotKey(snapshot)}>
                  {formatSession(snapshot.session_date)} · {snapshot.source} ·
                  {formatBytes(snapshot.size)} ·
                  {formatDate(snapshot.last_modified)}
                </option>
              {/each}
            </select>
          </div>
          <div class="flex flex-wrap gap-2">
            <Badge
              variant={data.storage.local ? "secondary" : "outline"}
              class={data.storage.local ? "" : "text-muted-foreground"}
            >
              local
            </Badge>
            <Badge
              variant={data.storage.r2 ? "secondary" : "outline"}
              class={data.storage.r2 ? "" : "text-muted-foreground"}
            >
              R2
            </Badge>
          </div>
        </div>

        <div class="flex flex-wrap gap-2">
          {#if data.bean.url}
            <a
              class={buttonVariants({ variant: "outline", size: "sm" })}
              href={data.bean.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              <ExternalLinkIcon class="mr-1 w-4 h-4" />
              Open live source
            </a>
          {/if}
          {#if canOpenScreenshot && selectedSnapshot}
            <a
              class={buttonVariants({ variant: "outline", size: "sm" })}
              href={contentUrl("screenshot", selectedSnapshot)}
              target="_blank"
              rel="noopener noreferrer"
            >
              <ImageIcon class="mr-1 w-4 h-4" />
              Open screenshot in new tab
            </a>
          {/if}
          <Button
            variant="outline"
            size="sm"
            onclick={copyCachePath}
            disabled={!selectedSnapshot}
          >
            <CopyIcon class="mr-1 w-4 h-4" />
            {copiedPath ? "Copied" : "Copy cache path"}
          </Button>
        </div>

        {#if data.warnings.length > 0}
          <div
            class="flex items-start gap-2 bg-amber-500/10 p-3 border border-amber-500/30 rounded-md text-amber-700 text-sm dark:text-amber-400"
          >
            <AlertTriangleIcon class="mt-0.5 w-4 h-4 shrink-0" />
            <ul class="space-y-1">
              {#each data.warnings as warning (warning)}
                <li>{warning}</li>
              {/each}
            </ul>
          </div>
        {/if}

        <div class="flex flex-wrap gap-1 border-b">
          {#each TABS as tab (tab.id)}
            <button
              type="button"
              class={cn(
                "-mb-px border-b-2 px-3 py-2 font-medium text-sm transition-colors",
                activeTab === tab.id
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
              onclick={() => selectTab(tab.id)}
            >
              {tab.label}
            </button>
          {/each}
        </div>

        {#if !selectedSnapshot}
          <div class="py-8 text-muted-foreground text-center text-sm">
            Select a snapshot to view its cached content.
          </div>
        {:else if activeTab === "screenshot"}
          {#if screenshotUnavailable || screenshotError}
            <div class="flex flex-col items-center gap-2 py-12 text-center">
              <ImageOffIcon class="w-10 h-10 text-muted-foreground" />
              <p class="font-medium">No screenshot in this snapshot.</p>
              <p class="text-muted-foreground text-sm">
                Try the rendered page or pick another snapshot.
              </p>
            </div>
          {:else}
            <div class="flex justify-center bg-muted/30 p-2 border rounded-md">
              <img
                src={contentUrl(
                  "screenshot",
                  selectedSnapshot,
                  selectedSnapshot.session_date,
                )}
                alt={`Screenshot of ${displayName || "the cached page"} from ${formatSession(
                  selectedSnapshot.session_date,
                )}`}
                class="max-h-[65vh] w-auto max-w-full rounded object-contain"
                onerror={() => (screenshotError = true)}
              />
            </div>
          {/if}
        {:else if activeTab === "html"}
          <div class="space-y-1">
            <iframe
              title="Cached rendered page"
              sandbox=""
              referrerpolicy="no-referrer"
              src={contentUrl("html", selectedSnapshot)}
              class="bg-white w-full h-[65vh] rounded-md border"
            ></iframe>
            <p class="text-muted-foreground text-xs">
              Scripts are disabled in this sandboxed preview.
            </p>
          </div>
        {:else if activeTab === "metadata"}
          {#if metadataLoading}
            <div class="py-8 text-muted-foreground text-center text-sm">
              Loading metadata…
            </div>
          {:else if metadataError}
            <div
              class="flex items-start gap-2 bg-destructive/10 p-3 border border-destructive/30 rounded-md text-destructive text-sm"
            >
              <AlertTriangleIcon class="mt-0.5 w-4 h-4 shrink-0" />
              <span>{metadataError}</span>
            </div>
          {:else if metadataJson}
            <pre
              class="bg-muted/40 p-3 border rounded-md max-h-[60vh] overflow-auto text-xs whitespace-pre-wrap break-all">{metadataJson}</pre>
          {:else}
            <div class="py-8 text-muted-foreground text-center text-sm">
              No metadata returned for this snapshot.
            </div>
          {/if}
        {:else if activeTab === "raw"}
          <div class="flex flex-col items-start gap-2">
            <p class="text-muted-foreground text-sm">
              Download the original <code>.tar.gz</code> archive for this snapshot.
            </p>
            <a
              class={buttonVariants({ variant: "outline", size: "sm" })}
              href={contentUrl("raw", selectedSnapshot)}
              download={selectedSnapshot.filename}
            >
              <DownloadIcon class="mr-1 w-4 h-4" />
              Download {selectedSnapshot.filename}
            </a>
          </div>
        {/if}
      </div>
    {/if}

    <Dialog.Footer>
      <Button variant="outline" onclick={() => (open = false)}>Close</Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
