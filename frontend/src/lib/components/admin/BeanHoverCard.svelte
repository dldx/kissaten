<script lang="ts">
  import * as Tooltip from "$lib/components/ui/tooltip/index.js";
  import CoffeeBeanCard from "../CoffeeBeanCard.svelte";
  import type { CoffeeBean } from "$lib/api";
  import type { Snippet } from "svelte";

  let {
    bean,
    children,
  }: { bean: CoffeeBean; children: Snippet<[Record<string, any>]> } = $props();

  function handleTooltipContentClick(e: MouseEvent) {
    // Prevent tooltip content from stealing focus or triggering clicks on
    // the row underneath (same guard as BeanSearchCombobox).
    e.stopPropagation();
  }
</script>

<Tooltip.Provider>
  <Tooltip.Root delayDuration={300}>
    <Tooltip.Trigger>
      {#snippet child({ props })}
        {@render children({ props })}
      {/snippet}
    </Tooltip.Trigger>
    <Tooltip.Content
      side="bottom"
      align="start"
      class="hidden sm:block bg-transparent shadow-none p-0 border-none"
      sideOffset={10}
      onmousedown={handleTooltipContentClick}
    >
      <div class="w-80 pointer-events-none">
        <CoffeeBeanCard {bean} />
      </div>
    </Tooltip.Content>
  </Tooltip.Root>
</Tooltip.Provider>