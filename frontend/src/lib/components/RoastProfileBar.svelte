<script lang="ts">
  import { Trophy } from "lucide-svelte";

  interface RoastLevel {
    roast_level: string;
    count: number;
  }

  interface Props {
    roast_distribution: RoastLevel[];
    roasterSlug?: string;
    roasterName?: string;
  }

  let { roast_distribution, roasterSlug, roasterName }: Props = $props();

  // Canonical ordering for the 5 main roast buckets
  const ORDER: Array<{ key: string; label: string }> = [
    { key: "Light", label: "Light" },
    { key: "Medium-Light", label: "Medium-Light" },
    { key: "Medium", label: "Medium" },
    { key: "Medium-Dark", label: "Medium-Dark" },
    { key: "Dark", label: "Dark" },
  ];

  // Build a lookup of counts by canonical key (with fallbacks for spelling variants)
  const countByKey = $derived.by(() => {
    const map = new Map<string, number>();
    for (const item of roast_distribution) {
      const raw = item.roast_level.trim();
      const normalised =
        raw === "Extra-Light"
          ? "Light"
          : raw === "Medium Light" || raw === "Medium light"
            ? "Medium-Light"
            : raw === "Medium Dark" || raw === "Medium dark"
              ? "Medium-Dark"
              : raw;
      const current = map.get(normalised) ?? 0;
      map.set(normalised, current + item.count);
    }
    return map;
  });

  const buckets = $derived(
    ORDER.map((b) => ({
      key: b.key,
      label: b.label,
      count: countByKey.get(b.key) ?? 0,
    })),
  );

  const totalCount = $derived(buckets.reduce((sum, b) => sum + b.count, 0));

  // Each segment's left-anchored start percentage and width percentage.
  // Used to absolutely position labels above the bar with leader lines.
  const segments = $derived.by(() => {
    if (totalCount === 0) return [];
    let cursor = 0;
    return buckets
      .filter((b) => b.count > 0)
      .map((b) => {
        const pct = (b.count / totalCount) * 100;
        const start = cursor;
        cursor += pct;
        return { ...b, start, pct };
      });
  });

  // Colors per bucket (light → dark amber/brown).
  const COLOR_FOR_BUCKET: Record<
    string,
    { bg: string; text: string; border: string }
  > = {
    Light: {
      bg: "bg-amber-100",
      text: "text-amber-800",
      border: "border-amber-200",
    },
    "Medium-Light": {
      bg: "bg-amber-300",
      text: "text-amber-900",
      border: "border-amber-400",
    },
    Medium: {
      bg: "bg-amber-500",
      text: "text-amber-50",
      border: "border-amber-600",
    },
    "Medium-Dark": {
      bg: "bg-amber-700",
      text: "text-amber-50",
      border: "border-amber-800",
    },
    Dark: {
      bg: "bg-stone-800",
      text: "text-stone-50",
      border: "border-stone-900",
    },
  };

  // Highlight the dominant roast (if any has >50% of beans).
  const dominantKey = $derived.by(() => {
    if (totalCount === 0) return null;
    const max = Math.max(...buckets.map((b) => b.count));
    if (max / totalCount < 0.5) return null;
    return buckets.find((b) => b.count === max)?.key ?? null;
  });

  let hoveredKey = $state<string | null>(null);
  const anyHovered = $derived(hoveredKey !== null);

  // Width below which a segment is too small to label reliably. Below 5%,
  // the label stays hidden until the user hovers the segment.
  const MIN_LABEL_WIDTH_PCT = 5;
</script>

{#if totalCount > 0}
  <div
    class="space-y-3"
    role="img"
    aria-label={`Roast level distribution: ${segments
      .map((s) => `${s.label} ${Math.round(s.pct)}%`)
      .join(", ")}`}
  >
    <!-- Stacked horizontal bar with per-segment inline labels -->
    <div
      class="relative flex border border-gray-200 dark:border-slate-700 rounded-lg w-full h-12 overflow-hidden"
    >
      {#each segments as segment (segment.key)}
        {@const colors = COLOR_FOR_BUCKET[segment.key]}
        {@const isHovered = hoveredKey === segment.key}
        {@const showInline = segment.pct >= MIN_LABEL_WIDTH_PCT}
        <a
          href={roasterSlug
            ? `/search?roaster=${encodeURIComponent(roasterName)}&apply_location_defaults=false&roast_level=${encodeURIComponent(segment.key)}`
            : "/search"}
          title={`${segment.label}: ${segment.count} bean${segment.count === 1 ? "" : "s"} (${segment.pct.toFixed(0)}%)`}
          aria-label={`${segment.label}: ${segment.count} bean${segment.count === 1 ? "" : "s"} (${segment.pct.toFixed(0)}%)`}
          class={`relative flex flex-col justify-center items-center ${colors.bg} ${colors.text} border-r last:border-r-0 border-white/40 transition-opacity px-1 text-center`}
          class:opacity-30={anyHovered && !isHovered}
          style="width: {segment.pct}%; min-width: {segment.pct > 0 ? '1.25rem' : '0'}; transition: opacity 150ms ease;"
          onmouseenter={() => (hoveredKey = segment.key)}
          onmouseleave={() => (hoveredKey = null)}
        >
          {#if showInline}
            <span class="font-semibold text-xs leading-tight truncate w-full">
              {segment.label}
            </span>
            <span class="tabular-nums text-[10px] opacity-90 leading-tight">
              {segment.count} bean{segment.count > 1 ? 's' : ''}
            </span>
          {:else if isHovered}
            <span class="font-semibold tabular-nums text-[10px] leading-tight">
              {segment.count}
            </span>
          {/if}
        </a>
      {/each}
    </div>

    <!-- Above-bar callouts: only for narrow segments (< 5%) and only while
         hovered. Wide segments are already labeled inline inside the bar,
         so rendering a second label here would duplicate/overlap them and
         cause a visible shift between SSR and hydration. -->
    {#if anyHovered}
      <div class="relative w-full h-10">
        {#each segments as segment (segment.key)}
          {@const center = segment.start + segment.pct / 2}
          {@const isHovered = hoveredKey === segment.key}
          {@const largeEnough = segment.pct >= MIN_LABEL_WIDTH_PCT}
          {#if !largeEnough && isHovered}
            <div
              class="absolute flex flex-col items-center w-0"
              style="left: {center}%; transform: translateX(-50%);"
            >
              <!-- Leader line: sits above the label to connect it up to the bar -->
              <div
                class="bg-gray-300 dark:bg-slate-600 w-px h-2.5"
                aria-hidden="true"
              ></div>
              <div
                class="flex flex-col items-center bg-white/95 dark:bg-slate-800/95 shadow-sm px-1.5 py-1 border border-gray-200 dark:border-slate-600 rounded text-center whitespace-nowrap"
              >
                <span
                  class="font-semibold text-gray-900 dark:text-cyan-100 text-[11px] leading-none"
                >
                  {segment.label}
                </span>
                <span
                  class="mt-0.5 text-gray-500 dark:text-cyan-400/70 text-[10px] tabular-nums leading-none"
                >
                  {segment.count} bean{segment.count > 1 ? 's' : ''}
                </span>
              </div>
            </div>
          {/if}
        {/each}
      </div>
    {/if}

    <!-- Dominant roast callout -->
    {#if dominantKey}
      {@const dom = segments.find((s) => s.key === dominantKey)}
      {#if dom}
        <div
          class="flex items-center gap-2 font-medium text-gray-700 dark:text-cyan-300 text-xs"
        >
          <Trophy class="w-3.5 h-3.5 text-orange-500 dark:text-orange-400" aria-hidden="true" />
          <span>
            <span class="font-bold text-gray-900 dark:text-cyan-100">{dom.label}</span>
            dominates this roaster — {dom.count}
            {dom.count === 1 ? "bean" : "beans"}
            ({dom.pct.toFixed(0)}% of the catalogue)
          </span>
        </div>
      {/if}
    {/if}
  </div>
{/if}
