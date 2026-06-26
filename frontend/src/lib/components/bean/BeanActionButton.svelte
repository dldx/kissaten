<script lang="ts">
  import { Button } from "$lib/components/ui/button/index.js";
  import * as Dialog from "$lib/components/ui/dialog/index.js";
  import * as Popover from "$lib/components/ui/popover/index.js";
  import * as Command from "$lib/components/ui/command/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import {
    ExternalLink,
    QrCode,
    ChevronDown,
    Check,
    Copy,
  } from "lucide-svelte";
  import { api } from "$lib/api";
  import { db } from "$lib/db/localdb";
  import { dbUpdateTrigger } from "$lib/db/updates.svelte";
  import { getUserWithoutRedirect } from "$lib/api/auth.remote";
  import { addUtmParams } from "$lib/utils";
  import { currencyState } from "$lib/stores/currency.svelte";
  import QRCodeStyling from "qr-code-styling";
  import { browser } from "$app/environment";
  import { onMount, tick } from "svelte";

  interface Props {
    bean: any;
  }

  let { bean }: Props = $props();

  // Auth state
  let currentUser = $state<any>(null);
  const isLoggedIn = $derived(!!currentUser);

  // Bean saved status (local-first)
  let isBeanSaved = $state(false);
  let savedBeanId = $state<string | null>(null);

  $effect(() => {
    const url = bean?.bean_url_path;
    const _s = dbUpdateTrigger.savedBeans;
    const _c = dbUpdateTrigger.customBeans;
    if (!url) {
      isBeanSaved = false;
      savedBeanId = null;
      return;
    }

    (async () => {
      const saved = await db.savedBeans
        .where("beanUrlPath")
        .equals(url)
        .filter((b) => !b.deletedAt)
        .first();
      if (saved) {
        isBeanSaved = true;
        savedBeanId = saved.syncId;
        return;
      }
      const custom = await db.customBeans
        .where("beanUrlPath")
        .equals(url)
        .filter((b) => !b.deletedAt)
        .first();
      if (custom) {
        isBeanSaved = true;
        savedBeanId = custom.syncId;
        return;
      }
      isBeanSaved = false;
      savedBeanId = null;
    })();
  });

  // Selected primary action
  let selectedAction = $state<"view" | "beanconquerer">("view");

  // Disable BC option if user not logged in OR bean not saved
  const beanConquerorEnabled = $derived(isLoggedIn && isBeanSaved);

  // Fall back to view if the selected action becomes unavailable
  $effect(() => {
    if (!beanConquerorEnabled && selectedAction === "beanconquerer") {
      selectedAction = "view";
    }
  });

  // Popover open state
  let popoverOpen = $state(false);

  function openRoasterUrl() {
    if (!bean?.url) return;
    window.open(
      addUtmParams(bean.url, {
        source: "kissaten.app",
        medium: "referral",
        campaign: "bean_profile",
      }),
      "_blank",
      "noopener,noreferrer",
    );
  }

  // BeanConqueror share dialog state
  let shareDialogOpen = $state(false);
  let shareUrl = $state<string | null>(null);
  let shareUrlLoading = $state(false);
  let shareUrlError = $state<string | null>(null);
  let copiedShareUrl = $state(false);

  async function loadShareUrl() {
    const parts = bean?.bean_url_path?.split("/") ?? [];
    const roasterSlug = parts[1];
    const beanSlug = parts[2];
    if (!roasterSlug || !beanSlug) {
      shareUrlError = "Unable to generate share link.";
      return;
    }
    shareUrlLoading = true;
    shareUrlError = null;
    shareUrl = null;
    try {
      const res = await api.getBeanConquererShareUrl(
        roasterSlug,
        beanSlug,
        currencyState.selectedCurrency || undefined,
      );
      if (res?.success && res.data?.share_url) {
        shareUrl = res.data.share_url;
      } else {
        shareUrlError = "Unable to generate share link.";
      }
    } catch (e) {
      console.error("Failed to load BeanConqueror share URL:", e);
      shareUrlError = "Unable to generate share link.";
    } finally {
      shareUrlLoading = false;
    }
  }

  // Re-fetch the share link whenever the selected currency changes while the
  // dialog is open, so the embedded price stays in sync with the UI.
  let lastFetchedCurrency = $state<string | null>(null);
  $effect(() => {
    const current = currencyState.selectedCurrency || null;
    if (
      shareDialogOpen &&
      current !== lastFetchedCurrency &&
      (shareUrl || shareUrlError) // only re-fetch once we have a result to replace
    ) {
      lastFetchedCurrency = current;
      loadShareUrl();
    } else if (shareDialogOpen && lastFetchedCurrency === null) {
      lastFetchedCurrency = current;
    }
  });

  async function copyShareUrl() {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
      copiedShareUrl = true;
      setTimeout(() => (copiedShareUrl = false), 2000);
    } catch (e) {
      console.error("Failed to copy share URL:", e);
    }
  }

  function openShareUrl() {
    if (!shareUrl) return;
    window.open(shareUrl, "_blank", "noopener,noreferrer");
  }

  function handlePrimaryAction() {
    if (selectedAction === "view") {
      openRoasterUrl();
    } else {
      shareDialogOpen = true;
      loadShareUrl();
    }
  }

  // QR code rendering
  let qrContainer: HTMLDivElement | null = $state(null);
  let qrRenderFailed = $state(false);

  function renderQrCode(url: string) {
    if (!browser || !qrContainer) return;
    qrContainer.innerHTML = "";
    qrRenderFailed = false;
    try {
      const qr = new QRCodeStyling({
        width: 240,
        height: 240,
        type: "svg",
        data: url,
        margin: 4,
        qrOptions: {
          errorCorrectionLevel: "L",
        },
        dotsOptions: {
          color: "#000000",
          type: "rounded",
        },
        backgroundOptions: {
          color: "#ffffff",
        },
        cornersSquareOptions: {
          color: "#000000",
          type: "extra-rounded",
        },
        cornersDotOptions: {
          color: "#000000",
        },
      });
      qr.append(qrContainer);
    } catch (e) {
      console.warn("QR code too large to render:", e);
      qrRenderFailed = true;
    }
  }

  $effect(() => {
    const url = shareUrl;
    if (url && browser) {
      tick().then(() => renderQrCode(url));
    }
  });

  // Fetch auth state on mount
  onMount(async () => {
    try {
      currentUser = await getUserWithoutRedirect();
    } catch {
      /* guest user */
    }
  });
</script>

{#if !isLoggedIn}
  <Button
    onclick={openRoasterUrl}
    class="py-2 w-full h-auto text-center leading-tight whitespace-normal"
  >
    <ExternalLink class="mr-2 w-4 h-4 shrink-0" />
    <span>View on {bean.roaster}</span>
  </Button>
{:else}
  <div
    class="inline-flex w-full rounded-md shadow-sm overflow-hidden border border-input dark:border-cyan-500/20"
  >
    <Button
      onclick={handlePrimaryAction}
      class="py-2 w-full h-auto text-center leading-tight whitespace-normal rounded-r-none"
    >
      {#if selectedAction === "view"}
        <ExternalLink class="mr-2 w-4 h-4 shrink-0" />
        <span>View on {bean.roaster}</span>
      {:else}
        <QrCode class="mr-2 w-4 h-4 text-black shrink-0" />
        <span>Save to BeanConqueror</span>
      {/if}
    </Button>
    <Popover.Root bind:open={popoverOpen}>
      <Popover.Trigger
        class="inline-flex justify-center items-center   dark:border-l dark:border-cyan-500/20 bg-primary text-primary-foreground hover:bg-primary/90 rounded-none px-3 w-10 h-auto transition-colors"
        aria-label="Select action"
      >
        <ChevronDown class="opacity-50 w-4 h-4" />
      </Popover.Trigger>
      <Popover.Content class="p-0 w-[260px]" align="end">
        <Command.Root>
          <Command.List class="max-h-[240px] overflow-y-scroll no-scrollbar">
            <Command.Group>
              <Command.Item
                value="view"
                onSelect={() => {
                  selectedAction = "view";
                  popoverOpen = false;
                }}
                class="flex items-center gap-2 group"
              >
                <ExternalLink class="w-4 h-4 shrink-0 text-black dark:text-white group-data-selected:text-black dark:group-data-selected:text-black" />
                <span>View on {bean.roaster}</span>
                {#if selectedAction === "view"}
                  <Check class="ml-auto w-4 h-4 text-black dark:text-white shrink-0 group-data-selected:text-black dark:group-data-selected:text-black" />
                {/if}
              </Command.Item>
              <Command.Item
                value="save-beanconqueror"
                disabled={!beanConquerorEnabled}
                onSelect={() => {
                  if (!beanConquerorEnabled) return;
                  selectedAction = "beanconquerer";
                  popoverOpen = false;
                }}
                class="flex items-center gap-2 group"
                title={isLoggedIn && !isBeanSaved
                  ? "Save the bean to your vault first"
                  : undefined}
              >
                <QrCode class="w-4 h-4 shrink-0 text-black dark:text-white group-data-selected:text-black" />
                <span>Save to BeanConqueror</span>
                {#if isLoggedIn && !isBeanSaved}
                  <span
                    class="ml-auto text-[10px] text-muted-foreground uppercase tracking-wide shrink-0"
                    >Save first</span
                  >
                {:else if selectedAction === "beanconquerer"}
                  <Check class="ml-auto w-4 h-4 shrink-0 text-black dark:text-white group-data-selected:text-black" />
                {/if}
              </Command.Item>
            </Command.Group>
          </Command.List>
        </Command.Root>
      </Popover.Content>
    </Popover.Root>
  </div>
{/if}

<Dialog.Root bind:open={shareDialogOpen}>
  <Dialog.Content class="sm:max-w-md">
    <Dialog.Header>
      <Dialog.Title class="flex items-center gap-2">
        <QrCode class="w-5 h-5 text-cyan-500" />
        Save to BeanConqueror
      </Dialog.Title>
      <Dialog.Description>
        Scan this QR code or open the link to import {bean.name} by {bean.roaster}
        into the Beanconqueror app.
        {#if currencyState.selectedCurrency}
          The price will be embedded in {currencyState.selectedCurrency}.
        {:else if bean.currency}
          The price will be embedded in its native currency ({bean.currency}).
        {/if}
      </Dialog.Description>
    </Dialog.Header>

    {#if shareUrlLoading}
      <div class="flex justify-center items-center py-8">
        <span class="text-muted-foreground text-sm">Generating share link…</span
        >
      </div>
    {:else if shareUrlError}
      <div class="py-4 text-red-600 text-sm">
        {shareUrlError}
      </div>
    {:else if shareUrl}
      <div class="flex flex-col items-center gap-4">
        {#if !qrRenderFailed}
          <div class="bg-white p-3 border rounded-lg">
            <div
              bind:this={qrContainer}
              class="w-[240px] h-[240px]"
              aria-label="QR code for Beanconqueror share link"
            ></div>
          </div>
        {:else}
          <div
            class="bg-muted/30 p-4 border rounded-lg w-full text-center text-muted-foreground text-sm"
          >
            QR code can't be generated for this bean (too much data). Use the
            link or copy button below.
          </div>
        {/if}
        <div class="flex items-center gap-2 w-full">
          <Input
            value={shareUrl}
            readonly
            class="font-mono text-xs"
            onclick={(e: MouseEvent) =>
              (e.currentTarget as HTMLInputElement).select()}
          />
          <Button
            variant="outline"
            size="icon"
            onclick={copyShareUrl}
            aria-label="Copy share link"
          >
            <Copy class="w-4 h-4" />
            {#if copiedShareUrl}
              <span class="sr-only">Copied</span>
            {/if}
          </Button>
        </div>
      </div>
    {/if}

    <Dialog.Footer class="gap-2 sm:gap-2">
      <Button variant="outline" onclick={() => (shareDialogOpen = false)}>
        Close
      </Button>
      <Button onclick={openShareUrl} disabled={!shareUrl}>
        <ExternalLink class="mr-2 w-4 h-4" />
        Open in BeanConqueror
      </Button>
    </Dialog.Footer>
  </Dialog.Content>
</Dialog.Root>
