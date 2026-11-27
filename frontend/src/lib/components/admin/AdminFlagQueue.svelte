<script lang="ts">
  import * as Card from "$lib/components/ui/card/index.js";
  import CheckCheckIcon from "lucide-svelte/icons/check-check";
  import type { FlagQueueIcon } from "./flagQueue";
  import BeanHoverCard from "./BeanHoverCard.svelte";
  import AdminFlagQueueRow from "./AdminFlagQueueRow.svelte";
  import type { FlagQueueItem } from "./flagQueue";

  let {
    sectionId,
    title,
    description,
    loading,
    error,
    pendingItems,
    handledItems = [],
    handledTitle = "Previously decided",
    emptyIcon = CheckCheckIcon,
    emptyText = "Nothing awaiting review. ✓",
    pendingEmptyIcon = emptyIcon,
    pendingEmptyText = emptyText,
  }: {
    sectionId: string;
    title: string;
    description: string;
    loading: boolean;
    error: string;
    pendingItems: FlagQueueItem[];
    handledItems?: FlagQueueItem[];
    handledTitle?: string;
    emptyIcon?: FlagQueueIcon;
    emptyText?: string;
    pendingEmptyIcon?: FlagQueueIcon;
    pendingEmptyText?: string;
  } = $props();

  const totalCount = $derived(pendingItems.length + handledItems.length);
</script>

{#snippet emptyState(stateIcon: FlagQueueIcon, stateText: string)}
  {@const StateIcon = stateIcon}
  <Card.Root>
    <Card.Content class="py-12">
      <div class="flex flex-col items-center gap-3 text-muted-foreground">
        <StateIcon class="w-10 h-10" />
        <p class="font-medium">{stateText}</p>
      </div>
    </Card.Content>
  </Card.Root>
{/snippet}

{#snippet queueRow(item: FlagQueueItem, handled: boolean)}
  {#if item.bean}
    <BeanHoverCard bean={item.bean}>
      {#snippet children({ props })}
        <AdminFlagQueueRow {item} {handled} wrappedProps={props} />
      {/snippet}
    </BeanHoverCard>
  {:else}
    <AdminFlagQueueRow {item} {handled} />
  {/if}
{/snippet}

<section id={sectionId} class="space-y-3 scroll-mt-24">
  <div>
    <h2 class="font-semibold text-xl">{title}</h2>
    <p class="text-muted-foreground text-sm">{description}</p>
  </div>

  {#if loading}
    <div class="py-8 text-muted-foreground text-center text-sm">Loading…</div>
  {:else if error}
    <div class="py-8 text-destructive text-center text-sm">{error}</div>
  {:else if totalCount === 0}
    {@render emptyState(emptyIcon, emptyText)}
  {:else}
    {#if pendingItems.length > 0}
      <div class="space-y-2">
        {#each pendingItems as item (item.id)}
          {@render queueRow(item, false)}
        {/each}
      </div>
    {:else}
      {@render emptyState(pendingEmptyIcon, pendingEmptyText)}
    {/if}

    {#if handledItems.length > 0}
      <div class="space-y-2 pt-2">
        <h3 class="font-medium text-sm text-muted-foreground">
          {handledTitle}
        </h3>
        {#each handledItems as item (item.id)}
          {@render queueRow(item, true)}
        {/each}
      </div>
    {/if}
  {/if}
</section>
