<script lang="ts">
  import { PieChart, type ArcLabelPlacement } from "layerchart/svg";
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
      labels={{
        placement: labelPlacement,
        offset: 12,
        value: "key",
        class: "text-xs fill-gray-700 dark:fill-cyan-100",
      }}
      tooltipContext={false}
      height={320}
    />
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
