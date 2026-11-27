<script lang="ts">
  import { Button } from "$lib/components/ui/button/index.js";
  import * as Card from "$lib/components/ui/card/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import { cn, formatPrice } from "$lib/utils";
  import type { FlagQueueItem } from "./flagQueue";

  let {
    item,
    handled = false,
    wrappedProps = {},
  }: {
    item: FlagQueueItem;
    /** True when rendered in the "previously decided / handled" sub-list. */
    handled?: boolean;
    /** Extra props forwarded from BeanHoverCard's tooltip trigger when the row is hoverable. */
    wrappedProps?: Record<string, any>;
  } = $props();

  const rowClass = $derived(
    cn(wrappedProps.class, handled ? "opacity-75" : ""),
  );
</script>

<Card.Root {...wrappedProps} class={rowClass}>
  <Card.Content class="pt-6">
    <div
      class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-4"
    >
      <div class="flex-1 min-w-0 space-y-1">
        <div class="flex flex-wrap items-center gap-2">
          {#if item.bean?.image_url}
            <img
              src={item.bean.image_url}
              alt=""
              class="bg-muted w-10 h-10 rounded object-cover shrink-0"
            />
          {:else if item.icon}
            {@const Icon = item.icon}
            <Icon class="w-4 h-4 text-muted-foreground shrink-0" />
          {/if}
          <p class="font-semibold truncate">
            {item.bean?.name ?? item.displayName}
          </p>
          {#each item.badges ?? [] as badge (badge.label)}
            <Badge
              variant={badge.variant ?? "secondary"}
              class={badge.className}
            >
              {badge.label}
            </Badge>
          {/each}
        </div>

        {#if item.bean?.price != null}
          <p class="text-muted-foreground text-sm">
            {formatPrice(item.bean.price, item.bean.currency)}
          </p>
        {/if}

        <div
          class="flex flex-wrap gap-x-3 gap-y-0.5 text-muted-foreground text-xs"
        >
          {#if item.pathLabel}
            <a href={"/roasters" + item.pathLabel} class="hover:underline">
              {item.pathLabel}
            </a>
          {/if}
          {#if item.bean?.url}
            <a
              href={item.bean.url}
              target="_blank"
              rel="noopener noreferrer"
              class="hover:underline"
            >
              Source ↗
            </a>
          {/if}
          {#if item.caption}
            <span title={item.captionTitle ?? item.caption}>
              {item.caption}
            </span>
          {/if}
        </div>
      </div>

      <div class="flex flex-wrap gap-2 sm:shrink-0 sm:justify-end">
        {#if item.inlineError}
          <p class="w-full text-destructive text-xs text-end">
            {item.inlineError}
          </p>
        {/if}
        {#each item.actions as action (action.label)}
          {@const Icon = action.icon}
          <Button
            size="sm"
            variant={action.variant ?? "outline"}
            disabled={action.disabled}
            onclick={action.onClick}
          >
            {#if Icon}
              <Icon class="mr-1 w-3.5 h-3.5" />
            {/if}
            {action.label}
          </Button>
        {/each}
      </div>
    </div>
  </Card.Content>
</Card.Root>
