<script lang="ts">
  import type { PageData } from "./$types";
  import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
  import PaginationControls from "$lib/components/PaginationControls.svelte";
  import SortControls from "$lib/components/SortControls.svelte";
  import BackButton from "$lib/components/BackButton.svelte";
  import FlavourProfileDonut from "$lib/components/FlavourProfileDonut.svelte";
  import RoastProfileBar from "$lib/components/RoastProfileBar.svelte";
  import * as Breadcrumb from "$lib/components/ui/breadcrumb";
  import { Card, CardContent } from "$lib/components/ui/card";
  import {
    MapPin,
    Coffee,
    Award,
    Search,
    Sparkles,
    Globe,
    Flame,
    Trophy,
    Leaf,
    Droplets,
  } from "lucide-svelte";
  import { page } from "$app/state";
  import { goto } from "$app/navigation";
  import { toAbsoluteUrl } from "$lib/seo";
  import { getCategoryEmoji } from "$lib/utils";
  import { onMount } from "svelte";
  import "iconify-icon";

  let { data }: { data: PageData } = $props();

  const roaster = $derived(data.roaster);
  const beans = $derived(data.beans || []);
  const pagination = $derived(data.pagination);
  const queryParams = $derived(data.queryParams);

  const hasAwards = $derived.by(() => {
    const awards = roaster?.awards;
    if (Array.isArray(awards)) return awards.length > 0;
    if (typeof awards === "string") return awards.trim().length > 0;
    return Boolean(awards);
  });

  const hasEnoughRoastData = $derived.by(() => {
    if (!data.roast_distribution || data.roast_distribution.length === 0) return false;
    const total = data.roast_distribution.reduce(
      (sum, r) => sum + (r.count ?? 0),
      0,
    );
    return total >= 10;
  });

  // --- Uniqueness report helpers --------------------------------------------
  // The backend returns a multi-dimensional UniquenessReport. The headline
  // adapts its wording per dimension (e.g. "skews Ethiopia in sourcing" vs
  // "skews Stone Fruit in flavour"), and secondary dimensions render as
  // chips that link to the relevant exploration page.

  const DIMENSION_NOUN: Record<string, string> = {
    flavour: "tasting notes",
    origin: "beans",
    process: "beans",
    varietal: "varietal mentions",
  };

  const uniquenessTop = $derived(data.uniqueness?.top ?? null);
  const uniquenessChips = $derived(
    data.uniqueness?.by_dimension ? Object.values(data.uniqueness.by_dimension) : [],
  );

  // Per-dimension grammatical templates. Each returns the four pieces that
  // make up the two-sentence uniqueness statement, with the standout label
  // inserted as a bold span in the right place. Flavour/process categories
  // are lowercased inside the detail sentence; origin/varietal labels keep
  // their proper-case spelling.
  function uniquenessSentence(insight: {
    dimension: string;
    display_label: string;
    this_roaster_pct: number;
    global_pct: number;
    lift: number;
    percentile: number;
    sample_size: number;
  }) {
    const name = roaster?.name ?? "This roaster";
    const label = insight.display_label;
    const pct = Math.round(insight.percentile);
    const thisPct = insight.this_roaster_pct.toFixed(1);
    const globalPct = insight.global_pct.toFixed(1);
    const lift = `${insight.lift > 0 ? "+" : ""}${insight.lift.toFixed(1)}`;
    const sample = insight.sample_size;

    switch (insight.dimension) {
      case "flavour":
        return {
          headlinePre: `${name}'s tasting notes skew`,
          headlinePost: ` — more so than ${pct}% of roasters.`,
          detailPre: `${thisPct}% of their tasting notes are`,
          detailLabel: label.toLowerCase(),
          detailPost: `, versus ${globalPct}% on average across the catalogue (${lift} pts, based on ${sample} notes).`,
        };
      case "origin":
        return {
          headlinePre: `${name}'s sourcing skews`,
          headlinePost: ` — more so than ${pct}% of roasters.`,
          detailPre: `${thisPct}% of their beans come from`,
          detailLabel: label,
          detailPost: `, versus ${globalPct}% on average across the catalogue (${lift} pts, based on ${sample} beans).`,
        };
      case "process":
        return {
          headlinePre: `${name}'s processing skews`,
          headlinePost: ` — more so than ${pct}% of roasters.`,
          detailPre: `${thisPct}% of their beans are processed as`,
          detailLabel: label.toLowerCase(),
          detailPost: `, versus ${globalPct}% on average across the catalogue (${lift} pts, based on ${sample} beans).`,
        };
      case "varietal":
        return {
          headlinePre: `${name}'s varietals skew`,
          headlinePost: ` — more so than ${pct}% of roasters.`,
          detailPre: `${thisPct}% of their varietal mentions are`,
          detailLabel: label,
          detailPost: `, versus ${globalPct}% on average across the catalogue (${lift} pts, based on ${sample} mentions).`,
        };
      default:
        return {
          headlinePre: `${name}'s catalogue skews`,
          headlinePost: ` — more so than ${pct}% of roasters.`,
          detailPre: `${thisPct}% of their beans are`,
          detailLabel: label.toLowerCase(),
          detailPost: `, versus ${globalPct}% on average across the catalogue (${lift} pts, based on ${sample} beans).`,
        };
    }
  }

  const uniquenessSentenceTop = $derived(
    uniquenessTop ? uniquenessSentence(uniquenessTop) : null,
  );

  function dimensionIcon(dimension: string) {
    switch (dimension) {
      case "flavour":
        return Sparkles;
      case "origin":
        return MapPin;
      case "process":
        return Droplets;
      case "varietal":
        return Leaf;
      default:
        return Trophy;
    }
  }

  let flavourChartMounted = $state(false);
  onMount(() => {
    requestAnimationFrame(() => {
      flavourChartMounted = true;
    });
  });

  const ogImage = $derived(
    toAbsoluteUrl(`/og/roaster/${page.params.roaster_name || ""}`),
  );

  const logoSrc = $derived(
    `/static/data/roasters/${roaster?.slug || page.params.roaster_name || ""}/logo_sticker.png`,
  );

  let searchQuery = $state("");

  function updateUrl(newParams: Record<string, string | number>) {
    const url = new URL(page.url);
    Object.entries(newParams).forEach(([key, value]) => {
      if (value) {
        url.searchParams.set(key, value.toString());
      } else {
        url.searchParams.delete(key);
      }
    });
    goto(url.toString(), {
      replaceState: true,
      noScroll: true,
    });
  }

  function handleSort(sortBy: string, sortOrder: string) {
    updateUrl({
      sort_by: sortBy,
      sort_order: sortOrder,
      page: 1,
    });
  }

  function handlePageChange(newPage: number) {
    updateUrl({ page: newPage });
  }

  function handleSearchInput(e: Event & { currentTarget: HTMLInputElement }) {
    const value = e.currentTarget.value;
    searchQuery = value;
  }

  function submitSearch() {
    const url = new URL(page.url);
    if (searchQuery.trim()) {
      url.searchParams.set("q", searchQuery.trim());
    } else {
      url.searchParams.delete("q");
    }
    url.searchParams.set("page", "1");
    goto(url.toString(), { noScroll: true });
  }
</script>

<svelte:head>
  <title>{roaster?.name ?? "Roaster"} | Coffee Roaster | Kissaten</title>
  <meta
    name="description"
    content={`Browse coffee beans roasted by ${roaster?.name ?? "this roaster"}${roaster?.location ? ` in ${roaster.location}` : ""}.`}
  />
  <link rel="canonical" href={`https://kissaten.app${page.url.pathname}`} />
  <meta property="og:image" content={ogImage} />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />
  <meta
    property="og:image:alt"
    content={`${roaster?.name || "Roaster"} coffee roaster profile`}
  />
  <meta name="twitter:image" content={ogImage} />
  <meta
    name="twitter:image:alt"
    content={`${roaster?.name || "Roaster"} coffee roaster profile`}
  />
</svelte:head>

<div class="mx-auto px-4 py-8 max-w-7xl container">
  <Breadcrumb.Root class="mb-6">
    <Breadcrumb.List>
      <Breadcrumb.Item>
        <Breadcrumb.Link href="/">Home</Breadcrumb.Link>
      </Breadcrumb.Item>
      <Breadcrumb.Separator />
      <Breadcrumb.Item>
        <Breadcrumb.Link href="/roasters">Roasters</Breadcrumb.Link>
      </Breadcrumb.Item>
      <Breadcrumb.Separator />
      <Breadcrumb.Item>
        <Breadcrumb.Page class="max-w-[120px] sm:max-w-none truncate">
          {roaster?.name ?? page.params.roaster_name}
        </Breadcrumb.Page>
      </Breadcrumb.Item>
    </Breadcrumb.List>
  </Breadcrumb.Root>

  <BackButton />

  {#if roaster}
    <!-- Header + About + Uniqueness -->
    <div
      class="bg-gradient-to-br from-white dark:from-slate-800/80 to-orange-50/50 dark:to-slate-800/40 shadow-sm mb-8 p-8 border border-orange-200 dark:border-cyan-500/30 rounded-xl"
    >
      <div
        class="flex md:flex-row flex-col justify-between md:items-start gap-6 mb-6"
      >
        <div class="flex items-start gap-4 min-w-0">
          <div
            class="flex justify-center items-center bg-gray-50 dark:bg-slate-400/60 border border-gray-200 dark:border-slate-600 rounded-lg w-28 sm:w-36 md:w-44 h-28 sm:h-36 md:h-44 overflow-hidden shrink-0"
          >
            <img
              src={logoSrc}
              alt="{roaster.name} logo"
              class="max-w-full max-h-full object-contain"
            />
          </div>
          <div class="min-w-0">
            <h1
              class="font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl tracking-tight"
            >
              {roaster.name}
            </h1>
            {#if roaster.location || roaster.website}
              <div class="flex items-center gap-2 mt-2">
                {#if roaster.location}
                  <div
                    class="flex items-center gap-1.5 bg-gray-100 dark:bg-slate-700/60 px-2.5 py-1.5 rounded-md text-gray-600 dark:text-cyan-300/80"
                    title={roaster.location}
                  >
                    {#if roaster.location_codes && roaster.location_codes[0]}
                      <iconify-icon
                        icon={`circle-flags:${roaster.location_codes[0].toLowerCase()}`}
                        class="text-lg"
                      ></iconify-icon>
                    {:else}
                      <MapPin class="w-4 h-4" />
                    {/if}
                    <span class="font-medium text-sm">{roaster.location}</span>
                  </div>
                {/if}
                {#if roaster.website}
                  <a
                    href={roaster.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={roaster.website}
                    aria-label="Visit website"
                    class="inline-flex justify-center items-center bg-gray-100 hover:bg-gray-200 dark:bg-slate-700/60 dark:hover:bg-slate-600/60 p-2 rounded-md text-gray-600 hover:text-gray-900 dark:hover:text-cyan-100 dark:text-cyan-300/80 transition-colors"
                  >
                    <Globe class="w-4 h-4" />
                  </a>
                {/if}
              </div>
            {/if}
          </div>
        </div>
      </div>

      <!-- Awards / Badges -->
      {#if hasAwards}
        <div class="mb-6">
          <h2
            class="flex items-center gap-2 mb-3 font-bold text-gray-900 dark:text-cyan-100 text-xl"
          >
            <Award class="w-5 h-5" />
            Awards &amp; Recognition
          </h2>
          <div
            class="flex flex-wrap items-center gap-2 bg-white/50 dark:bg-slate-900/40 p-4 border border-gray-200 dark:border-slate-700 border-dashed rounded-lg"
          >
            {#if Array.isArray(roaster?.awards)}
              {#each roaster!.awards as award (award)}
                <span
                  class="inline-flex items-center gap-1 bg-white dark:bg-slate-800 shadow-sm px-3 py-1 border border-gray-200 dark:border-slate-600 rounded-full font-medium text-gray-700 dark:text-cyan-200 text-sm"
                >
                  <Award class="w-3.5 h-3.5" />
                  {typeof award === "string" ? award : award.name}
                </span>
              {/each}
            {:else if typeof roaster?.awards === "string"}
              <span
                class="inline-flex items-center gap-1 bg-white dark:bg-slate-800 shadow-sm px-3 py-1 border border-gray-200 dark:border-slate-600 rounded-full font-medium text-gray-700 dark:text-cyan-200 text-sm"
              >
                <Award class="w-3.5 h-3.5" />
                {roaster.awards}
              </span>
            {:else}
              <span class="text-gray-500 dark:text-cyan-400/70 text-sm italic">
                Awards and badges for {roaster.name} will be displayed here when available.
              </span>
            {/if}
          </div>
        </div>
      {/if}

      <!-- About -->
      <div class="mb-6">
        <h2
          class="flex items-center gap-2 mb-3 font-bold text-gray-900 dark:text-cyan-100 text-xl"
        >
          About {roaster.name}
        </h2>
        {#if roaster.description && roaster.description.trim()}
          <p
            class="text-gray-700 dark:text-cyan-200/90 text-base leading-relaxed whitespace-pre-line"
          >
            {roaster.description}
          </p>
        {:else}
          <div
            class="bg-white/50 dark:bg-slate-900/40 p-4 border border-orange-200 dark:border-slate-700 border-dashed rounded-lg text-gray-500 dark:text-cyan-400/70 text-sm italic"
          >
            A roaster description will appear here once available.
          </div>
        {/if}
      </div>

      {#if uniquenessTop && uniquenessSentenceTop}
        <!-- What Makes Them Unique -->
        <div
          class="pt-6 border-orange-200/60 dark:border-cyan-500/20 border-t"
        >
          <div class="min-w-0">
            <div
              class="flex items-center gap-2 mb-1 font-semibold text-orange-700 dark:text-orange-300 text-sm uppercase tracking-wider"
            >
              <Trophy class="w-4 h-4" />
              What Makes Them Unique
            </div>
            <p
              class="text-gray-900 dark:text-cyan-100 text-base leading-relaxed"
            >
              {uniquenessSentenceTop.headlinePre}
              <strong
                class="font-semibold text-orange-700 dark:text-orange-300"
              >
                {uniquenessTop.display_label}
              </strong>{uniquenessSentenceTop.headlinePost}
            </p>
            <p
              class="mt-2 text-gray-600 dark:text-cyan-300/80 text-sm leading-relaxed"
            >
              {uniquenessSentenceTop.detailPre}
              <strong class="font-semibold">{uniquenessSentenceTop.detailLabel}</strong>{uniquenessSentenceTop.detailPost}
            </p>

          </div>
        </div>
      {/if}
    </div>

    {#if hasEnoughRoastData}
      <!-- Roaster Profile: Flavour + Roast -->
      <div class="gap-6 grid md:grid-cols-2 mb-8">
        <!-- Flavour Profile -->
        <div
          class="bg-white dark:bg-slate-800/80 shadow-sm p-6 border border-gray-200 rounded-xl"
        >
          <h2
            class="flex items-center gap-2 mb-4 font-bold text-gray-900 dark:text-cyan-100 text-xl"
          >
            <Sparkles class="w-5 h-5" />
            Flavour Profile
          </h2>
          {#if flavourChartMounted && data.flavour_categories && data.flavour_categories.length > 0}
            <FlavourProfileDonut
              categories={data.flavour_categories}
              roasterSlug={roaster.slug}
            />
          {:else if data.flavour_categories && data.flavour_categories.length > 0}
            <Card
              class="bg-white/50 dark:bg-slate-900/50 border-slate-200 dark:border-cyan-500/20 h-[400px] overflow-hidden animate-pulse"
            >
              <CardContent class="flex justify-center items-center w-full h-full">
                <div
                  class="bg-slate-200 dark:bg-slate-800 rounded-full w-64 h-64"
                ></div>
              </CardContent>
            </Card>
          {:else if !data.flavour_categories}
            <Card
              class="bg-white/50 dark:bg-slate-900/50 border-slate-200 dark:border-cyan-500/20 h-[400px] overflow-hidden animate-pulse"
            >
              <CardContent class="flex justify-center items-center w-full h-full">
                <div
                  class="bg-slate-200 dark:bg-slate-800 rounded-full w-64 h-64"
                ></div>
              </CardContent>
            </Card>
          {:else}
            <div
              class="bg-gray-50 dark:bg-slate-900/40 p-4 border border-gray-200 dark:border-slate-700 border-dashed rounded-lg text-gray-500 dark:text-cyan-400/70 text-sm italic"
            >
              Not enough categorised tasting notes yet to build a flavour profile.
            </div>
          {/if}
        </div>

        <!-- Roast Profile -->
        <div
          class="bg-white dark:bg-slate-800/80 shadow-sm p-6 border border-gray-200 rounded-xl"
        >
          <h2
            class="flex items-center gap-2 mb-4 font-bold text-gray-900 dark:text-cyan-100 text-xl"
          >
            <Flame class="w-5 h-5" />
            Roast Profile
          </h2>
          <RoastProfileBar
            roast_distribution={data.roast_distribution}
            roasterSlug={roaster.slug}
            roasterName={roaster.name}
          />
        </div>
      </div>
    {:else}
      <!-- Flavour Profile only (insufficient roast data for chart) -->
      <div class="mb-8">
        <div
          class="bg-white dark:bg-slate-800/80 shadow-sm p-6 border border-gray-200 rounded-xl"
        >
          <h2
            class="flex items-center gap-2 mb-4 font-bold text-gray-900 dark:text-cyan-100 text-xl"
          >
            <Sparkles class="w-5 h-5" />
            Flavour Profile
          </h2>
          {#if flavourChartMounted && data.flavour_categories && data.flavour_categories.length > 0}
            <FlavourProfileDonut
              categories={data.flavour_categories}
              roasterSlug={roaster.slug}
            />
          {:else if data.flavour_categories && data.flavour_categories.length > 0}
            <Card
              class="bg-white/50 dark:bg-slate-900/50 border-slate-200 dark:border-cyan-500/20 h-[400px] overflow-hidden animate-pulse"
            >
              <CardContent class="flex justify-center items-center w-full h-full">
                <div
                  class="bg-slate-200 dark:bg-slate-800 rounded-full w-64 h-64"
                ></div>
              </CardContent>
            </Card>
          {:else if !data.flavour_categories}
            <Card
              class="bg-white/50 dark:bg-slate-900/50 border-slate-200 dark:border-cyan-500/20 h-[400px] overflow-hidden animate-pulse"
            >
              <CardContent class="flex justify-center items-center w-full h-full">
                <div
                  class="bg-slate-200 dark:bg-slate-800 rounded-full w-64 h-64"
                ></div>
              </CardContent>
            </Card>
          {:else}
            <div
              class="bg-gray-50 dark:bg-slate-900/40 p-4 border border-gray-200 dark:border-slate-700 border-dashed rounded-lg text-gray-500 dark:text-cyan-400/70 text-sm italic"
            >
              Not enough categorised tasting notes yet to build a flavour profile.
            </div>
          {/if}
        </div>
      </div>
    {/if}

    <!-- Coffee Beans Section -->
    <div
      class="bg-white dark:bg-slate-800/80 shadow-sm p-6 border border-gray-200 rounded-xl"
    >
      <!-- Section Header -->
      <div
        class="flex sm:flex-row flex-col sm:justify-between sm:items-center gap-4 mb-6"
      >
        <h2 class="font-bold text-gray-900 dark:text-emerald-300 text-2xl">
          Coffee Beans from {roaster.name}
        </h2>

        <div
          class="flex sm:flex-row flex-col items-stretch sm:items-center gap-3 w-full sm:w-auto"
        >
          <div class="relative w-full sm:w-72">
            <Search
              class="top-1/2 left-3 absolute w-4 h-4 text-gray-500 dark:text-cyan-400/70 -translate-y-1/2 transform"
            />
            <input
              type="search"
              value={searchQuery}
              oninput={handleSearchInput}
              onkeydown={(e) => {
                if (e.key === "Enter") submitSearch();
              }}
              placeholder="Search beans by name, origin, or notes..."
              class="bg-white dark:bg-slate-700/60 px-3 py-2 pl-10 border border-gray-200 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 rounded-md outline-none focus:ring-1 focus:ring-orange-500 dark:focus:ring-emerald-500/50 w-full h-10 text-gray-900 dark:placeholder:text-cyan-400/70 dark:text-cyan-200 placeholder:text-gray-500 text-sm transition-all"
            />
          </div>

          <SortControls
            currentSort={queryParams.sort_by}
            currentOrder={queryParams.sort_order}
            onSort={(e) => handleSort(e.sortBy, e.sortOrder)}
          />
        </div>
      </div>

      <!-- Coffee Beans Grid -->
      {#await beans}
        <div
          class="gap-4 sm:gap-6 grid grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 mb-8"
        >
          {#each Array(8) as _, i (i)}
            <Card
              class="bg-white/50 dark:bg-slate-900/50 border-slate-200 dark:border-cyan-500/20 h-[500px] overflow-hidden animate-pulse"
            >
              <div class="bg-slate-200 dark:bg-slate-800 w-full h-48"></div>
              <CardContent class="p-6">
                <div
                  class="bg-slate-200 dark:bg-slate-800 mb-4 rounded w-1/3 h-4"
                ></div>
                <div
                  class="bg-slate-200 dark:bg-slate-800 mb-2 rounded w-full h-8"
                ></div>
                <div
                  class="bg-slate-200 dark:bg-slate-800 mb-8 rounded w-2/3 h-4"
                ></div>
                <div class="flex gap-2">
                  <div
                    class="bg-slate-200 dark:bg-slate-800 rounded-full w-16 h-6"
                  ></div>
                  <div
                    class="bg-slate-200 dark:bg-slate-800 rounded-full w-16 h-6"
                  ></div>
                </div>
              </CardContent>
            </Card>
          {/each}
        </div>
      {:then beans}
        {#if beans && beans.length > 0}
          <div
            class="gap-4 sm:gap-6 grid grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 mb-8"
          >
            {#each beans as bean (bean.bean_url_path || `${bean.id}-${bean.name}`)}
              <CoffeeBeanCard {bean} />
            {/each}
          </div>

          <!-- Pagination -->
          {#await pagination}
            <!-- pagination still loading -->
          {:then pagination}
            {#if pagination && pagination.total_pages > 1}
              <PaginationControls
                {pagination}
                onPageChange={(newPage) => handlePageChange(newPage)}
              />
            {/if}
          {:catch}
            <!-- pagination failed -->
          {/await}
        {:else}
          <div class="py-12 text-center">
            <Coffee
              class="mx-auto mb-4 w-12 h-12 text-gray-500 dark:text-cyan-400/70"
            />
            <h3
              class="mb-2 font-semibold text-gray-900 dark:text-cyan-100 text-xl"
            >
              No beans yet
            </h3>
            <p class="text-gray-600 dark:text-cyan-300/80">
              We haven't cataloged any beans from {roaster.name} yet.
            </p>
          </div>
        {/if}
      {:catch}
        <div class="py-12 text-center">
          <p class="text-gray-600 dark:text-cyan-300/80">
            Failed to load beans for {roaster.name}.
          </p>
        </div>
      {/await}
    </div>
  {/if}
</div>
