<script lang="ts">
  import { PieChart, Arc, ArcLabel, type ArcLabelPlacement } from "layerchart/svg";
  import { fade } from "svelte/transition";
  import { cubicOut } from "svelte/easing";
  import {
    getFlavourCategoryHexColor,
    FLAVOUR_CATEGORY_ORDER,
  } from "$lib/utils";

  interface FlavourCategory {
    primary_category: string;
    count: number;
    percentage: number;
  }

  interface Props {
    categories: FlavourCategory[];
    roasterSlug?: string;
  }

  let { categories, roasterSlug }: Props = $props();

  // Sort by canonical order, falling back to the input order for unknown categories
  const ordered = $derived.by(() => {
    const orderIndex = new Map<string, number>();
    FLAVOUR_CATEGORY_ORDER.forEach((cat, i) => orderIndex.set(cat, i));

    return [...categories].sort((a, b) => {
      const ai = orderIndex.has(a.primary_category)
        ? orderIndex.get(a.primary_category)!
        : Number.MAX_SAFE_INTEGER;
      const bi = orderIndex.has(b.primary_category)
        ? orderIndex.get(b.primary_category)!
        : Number.MAX_SAFE_INTEGER;
      if (ai !== bi) return ai - bi;
      return b.percentage - a.percentage;
    });
  });

  const totalCount = $derived(ordered.reduce((sum, c) => sum + c.count, 0));

  // Map to layerchart's expected data shape and pre-compute color range so the
  // donut slices use the project's canonical flavour palette.
  const chartData = $derived(
    ordered.map((c) => ({
      key: c.primary_category,
      value: c.count,
      percentage: c.percentage,
    })),
  );

  const cRange = $derived(
    ordered.map((c) => getFlavourCategoryHexColor(c.primary_category)),
  );

  const labelPlacement: ArcLabelPlacement = "callout";

  // Hide labels for tiny slices — callout leader lines overlap and become
  // unreadable when arcs are too small.
  const MIN_LABEL_PERCENT = 2;

  // When an arc is hovered, force-show its label (even if it would normally
  // be hidden for being too small) and hide all others so the callout has
  // room to render without overlap.
  let hoveredKey = $state<string | null>(null);
</script>

{#if ordered.length > 0}
  <div class="relative w-full">
    <PieChart
      data={chartData}
      key="key"
      value="value"
      {cRange}
      innerRadius={50}
      padding={{ top: 32, bottom: 32, left: 32, right: 32 }}
      tooltipContext={false}
      height={320}
      motion={{ type: "spring", stiffness: 0.4, damping: 0.85 }}
    >
      {#snippet arc({ props: arcProps })}
        {@const arcData = arcProps.data as
          | { key: string; value: number; percentage?: number }
          | undefined}
        {@const isHovered = hoveredKey !== null && hoveredKey === arcData?.key}
        {@const anyHovered = hoveredKey !== null}
        {@const showLabel =
          anyHovered ? isHovered : (arcData?.percentage ?? 0) >= MIN_LABEL_PERCENT}
        <Arc
          {...arcProps}
          opacity={anyHovered ? (isHovered ? 1 : 0.35) : 1}
          style="transition: opacity 150ms ease;"
          motion={{ type: "spring", stiffness: 0.4, damping: 0.85 }}
          onmouseenter={() => (hoveredKey = arcData?.key ?? null)}
          onmouseleave={() => (hoveredKey = null)}
        >
          {#snippet children({
            centroid,
            startAngle,
            endAngle,
            innerRadius,
            outerRadius,
            getArcTextProps,
          })}
            {#if showLabel}
              <g in:fade={{ duration: 180, easing: cubicOut }}>
                <ArcLabel
                  {centroid}
                  {startAngle}
                  {endAngle}
                  {innerRadius}
                  {outerRadius}
                  {getArcTextProps}
                  placement={labelPlacement}
                  offset={20}
                  value={arcData?.key ?? ""}
                  class="text-xs fill-gray-700 dark:fill-cyan-100"
                />
              </g>
            {/if}
          {/snippet}
        </Arc>
      {/snippet}
    </PieChart>
    <!-- Center label -->
    <div
      class="top-1/2 left-1/2 absolute -translate-x-1/2 -translate-y-1/2 transform text-center pointer-events-none"
    >
      <div
        class="font-bold text-gray-900 dark:text-cyan-100 text-2xl leading-none"
      >
        {totalCount.toLocaleString()}
      </div>
      <div
        class="mt-1 text-gray-500 dark:text-cyan-400/70 text-xs uppercase tracking-wider"
      >
        Notes
      </div>
    </div>
  </div>
{/if}
