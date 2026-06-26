<script lang="ts">
  interface RoastLevel {
    roast_level: string;
    count: number;
  }

  interface Props {
    roast_distribution: RoastLevel[];
    roasterSlug?: string;
  }

  let { roast_distribution, roasterSlug }: Props = $props();

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
      // Normalise common variants into the 5 canonical buckets
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

  const buckets = $derived.by(() => {
    return ORDER.map((b) => ({
      key: b.key,
      label: b.label,
      count: countByKey.get(b.key) ?? 0,
    }));
  });

  const totalCount = $derived(buckets.reduce((sum, b) => sum + b.count, 0));

  // Map canonical bucket → gradient color (light → dark amber/brown)
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

  // Highlight the dominant roast (if any has >50% of beans)
  const dominantKey = $derived.by(() => {
    if (totalCount === 0) return null;
    const max = Math.max(...buckets.map((b) => b.count));
    if (max / totalCount < 0.5) return null;
    return buckets.find((b) => b.count === max)?.key ?? null;
  });
</script>

{#if totalCount > 0}
  <div class="space-y-3">
    <!-- Stacked horizontal bar -->
    <div
      class="flex rounded-lg overflow-hidden w-full h-8 border border-gray-200 dark:border-slate-700"
      role="img"
      aria-label={`Roast level distribution: ${buckets
        .filter((b) => b.count > 0)
        .map((b) => `${b.label} ${Math.round((b.count / totalCount) * 100)}%`)
        .join(", ")}`}
    >
      {#each buckets as bucket (bucket.key)}
        {#if bucket.count > 0}
          {@const pct = (bucket.count / totalCount) * 100}
          {@const colors = COLOR_FOR_BUCKET[bucket.key]}
          <a
            href={roasterSlug
              ? `/search?roaster=${encodeURIComponent(roasterSlug)}`
              : "/search"}
            title={`${bucket.label}: ${bucket.count} bean${bucket.count === 1 ? "" : "s"} (${pct.toFixed(0)}%)`}
            class={`flex justify-center items-center ${colors.bg} ${colors.text} border-r last:border-r-0 border-white/40 transition-opacity hover:opacity-80`}
            style="width: {pct}%; min-width: {pct > 0 ? '2.5rem' : '0'};"
          >
            {#if pct >= 12}
              <span class="font-semibold text-xs tabular-nums">
                {bucket.count}
              </span>
            {/if}
          </a>
        {/if}
      {/each}
    </div>

    <!-- Legend -->
    <div class="flex flex-wrap gap-x-4 gap-y-2 text-xs">
      {#each buckets as bucket (bucket.key)}
        {@const colors = COLOR_FOR_BUCKET[bucket.key]}
        {@const pct = totalCount > 0 ? (bucket.count / totalCount) * 100 : 0}
        {@const isDominant = dominantKey === bucket.key}
        <div class="flex items-center gap-1.5">
          <span
            class={`inline-block rounded-sm w-3 h-3 ${colors.bg} ${bucket.count === 0 ? "opacity-30" : ""}`}
          ></span>
          <span
            class={`${bucket.count === 0 ? "text-gray-400 dark:text-cyan-500/40" : "text-gray-700 dark:text-cyan-300"}`}
          >
            {bucket.label}
          </span>
          {#if bucket.count > 0}
            <span class="text-gray-500 dark:text-cyan-400/70 tabular-nums">
              ({bucket.count}, {pct.toFixed(0)}%)
            </span>
          {/if}
          {#if isDominant}
            <span
              class="font-semibold text-orange-600 dark:text-orange-400 text-[10px] uppercase tracking-wider"
            >
              ★ Dominant
            </span>
          {/if}
        </div>
      {/each}
    </div>
  </div>
{/if}
