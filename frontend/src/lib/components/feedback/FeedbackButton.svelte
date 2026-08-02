<script lang="ts">
  import { Bug } from "lucide-svelte";
  import { browser } from "$app/environment";
  import { pwaState } from "$lib/pwa-install.svelte";
  import { openFeedbackDialog } from "$lib/stores/feedbackDialog.svelte";

  // On mobile, the layout has a bottom toolbar (z-50); the PWA prompt
  // (bottom-4, z-100) sits above it on installable browsers. Lift the
  // feedback button so it never overlaps with either.
  const bottomClass = $derived.by(() => {
    if (!browser) return "bottom-6";
    const isMobile = window.matchMedia("(max-width: 767px)").matches;
    if (!isMobile) return "bottom-6";
    return pwaState.isInstallable && !pwaState.isRejected
      ? "bottom-44"
      : "bottom-20";
  });
</script>

<button
  type="button"
  onclick={openFeedbackDialog}
  aria-label="Report an issue"
  title="Report an issue"
  class="fixed right-6 z-40 inline-flex justify-center items-center bg-background hover:bg-accent shadow-lg hover:shadow-xl p-0 border border-border rounded-full w-12 h-12 text-foreground transition-all duration-200 hover:scale-105 {bottomClass}"
>
  <Bug class="w-5 h-5" />
</button>
