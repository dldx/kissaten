<script lang="ts">
  import { Button, type ButtonProps } from "$lib/components/ui/button";
  import * as Dialog from "$lib/components/ui/dialog";
  import { Input } from "$lib/components/ui/input";
  import { QrCode, Copy, ExternalLink } from "lucide-svelte";
  import { api } from "$lib/api";
  import { currencyState } from "$lib/stores/currency.svelte";
  import QRCodeStyling from "qr-code-styling";
  import { browser } from "$app/environment";
  import { tick } from "svelte";

  interface Props {
    bean: any;
    variant?: ButtonProps["variant"];
    size?: ButtonProps["size"];
    label?: string;
    disabled?: boolean;
    disabledTitle?: string;
    class?: string;
  }

  let {
    bean,
    variant = "default",
    size = "default",
    label = "Save to BeanConqueror",
    disabled = false,
    disabledTitle = "",
    class: className = "",
  }: Props = $props();

  const isCustomBean = $derived(
    bean?.is_custom || bean?.bean_url_path?.startsWith("/custom/"),
  );

  let shareDialogOpen = $state(false);
  let shareUrl = $state<string | null>(null);
  let shareUrlLoading = $state(false);
  let shareUrlError = $state<string | null>(null);
  let copiedShareUrl = $state(false);
  let qrCode: QRCodeStyling | null = $state(null);
  let qrContainer: HTMLDivElement | null = $state(null);
  let qrRenderFailed = $state(false);
  let lastFetchedCurrency = $state<string | null>(null);

  async function loadShareUrl() {
    if (isCustomBean) {
      shareUrlLoading = true;
      shareUrlError = null;
      shareUrl = null;
      try {
        const res = await api.getCustomBeanConquererShareUrl(
          bean,
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
      return;
    }

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
  $effect(() => {
    const current = currencyState.selectedCurrency || null;
    if (
      shareDialogOpen &&
      current !== lastFetchedCurrency &&
      (shareUrl || shareUrlError)
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

  function openShareDialog() {
    shareDialogOpen = true;
    loadShareUrl();
  }

  function renderQrCode(url: string) {
    if (!browser || !qrContainer) return;
    qrContainer.innerHTML = "";
    qrRenderFailed = false;
    try {
      const qr = new QRCodeStyling({
        width: 360,
        height: 360,
        type: "svg",
        data: url,
        margin: 1,
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
      qrCode = qr;
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

  // Resize the QR code to fill the dialog. Uses a ResizeObserver on the
  // container so the QR code scales to whatever width the dialog has,
  // keeping the white quiet-zone minimal on both desktop and mobile.
  $effect(() => {
    if (!browser || !qrContainer || !qrCode) return;
    const observer = new ResizeObserver((entries) => {
      const size = Math.floor(entries[0].contentRect.width);
      if (size > 0) {
        qrCode.update({ width: size, height: size });
      }
    });
    observer.observe(qrContainer);
    return () => observer.disconnect();
  });

  const iconClass = $derived(
    size === "sm"
      ? "mr-1 w-3 h-3 shrink-0"
      : "mr-2 w-4 h-4 text-black shrink-0",
  );
</script>

<Button
  onclick={openShareDialog}
  {disabled}
  {variant}
  {size}
  title={disabled && disabledTitle ? disabledTitle : undefined}
  class={className}
>
  <QrCode class={iconClass} />
  <span>{label}</span>
</Button>

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
        <span class="text-muted-foreground text-sm">Generating share link…</span>
      </div>
    {:else if shareUrlError}
      <div class="py-4 text-red-600 text-sm">
        {shareUrlError}
      </div>
    {:else if shareUrl}
      <div class="flex flex-col items-center gap-4">
        {#if !qrRenderFailed}
          <div class="bg-white p-1 border rounded-lg w-full">
            <div
              bind:this={qrContainer}
              class="w-full aspect-square"
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
