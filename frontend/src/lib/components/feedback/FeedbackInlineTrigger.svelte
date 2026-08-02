<script lang="ts">
  import { Bug } from "lucide-svelte";
  import { openFeedbackDialog } from "$lib/stores/feedbackDialog.svelte";

  interface Props {
    label?: string;
  }

  let { label = "Report data issue" }: Props = $props();
</script>

<button
  type="button"
  onclick={openFeedbackDialog}
  class="inline-flex items-center justify-center gap-2 bg-background hover:bg-accent dark:bg-slate-800/60 dark:hover:bg-slate-700/60 dark:border-slate-700 border border-border rounded-md px-3 py-2 w-full text-sm transition-colors"
>
  <Bug class="w-4 h-4 text-red-500" />
  <span>{label}</span>
</button>
