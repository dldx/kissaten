<script lang="ts">
    import type { PageData } from "./$types";
    import GeographyBreadcrumb from "$lib/components/GeographyBreadcrumb.svelte";
    import RegionCard from "$lib/components/RegionCard.svelte";
    import {
        Users,
        MapPin,
        TrendingUp,
        Droplets,
        ArrowRight,
        Coffee,
        Warehouse,
        ArrowUpCircle,
        Leaf,
    } from "lucide-svelte";
    import { getProcessIcon } from "$lib/utils";
    import { api } from "$lib/api";
    import "iconify-icon";
    import { scale } from "svelte/transition";
    import { Input } from "$lib/components/ui/input/index.js";
    import { Search } from "lucide-svelte";

    import InsightCard from "$lib/components/InsightCard.svelte";

    let { data }: { data: PageData } = $props();
    const country = $derived(data.country);
    const regions = $derived(data.regions);

    let searchQuery = $state("");
    let filteredRegions = $derived(
        searchQuery.trim()
            ? regions.filter((r) =>
                  r.region_name
                      .toLowerCase()
                      .includes(searchQuery.toLowerCase()),
              )
            : regions,
    );

    // Prepare items for InsightCard
    const varietalItems = $derived(
        country?.varietals?.slice(0, 5).map((v) => ({
            label: v.variety,
            count: v.count,
            href: `/search?variety=${encodeURIComponent(v.variety)}&origin=${country.country_code}`,
        })) || [],
    );

    const processItems = $derived(
        country?.processing_methods
            ?.filter((m) => m.process.toLowerCase() !== "unknown")
            .slice(0, 5)
            .map((m) => ({
                label: m.process,
                count: m.count,
                icon: getProcessIcon(m.process),
                href: `/search?process=${encodeURIComponent(m.process)}&origin=${country.country_code}`,
            })) || [],
    );

    const noteItems = $derived(
        country?.common_tasting_notes?.slice(0, 5).map((n) => ({
            label: n.note,
            count: n.frequency,
            href: `/search?tasting_notes_query="${encodeURIComponent(n.note)}"&origin=${country.country_code}`,
        })) || [],
    );
</script>

<svelte:head>
    <title
        >{country?.country_name || country?.country_code} - Coffee Origins - Kissaten</title
    >
    <meta
        name="description"
        content="Explore coffee regions and farms from {country?.country_name}. {country
            ?.statistics.total_beans} beans from {country?.statistics
            .total_regions} regions."
    />
</svelte:head>

<div class="mx-auto px-4 py-8 max-w-7xl container">
    <GeographyBreadcrumb
        countryCode={country?.country_code}
        countryName={country?.country_name}
    />

    {#if country}
        <!-- Header Section -->
        <div
            class="bg-white dark:bg-slate-800/80 shadow-sm mb-8 p-8 border border-gray-200 dark:border-slate-700 rounded-xl"
        >
            <div class="flex md:flex-row flex-col items-center gap-8 mb-8">
                <div
                    class="flex justify-center items-center bg-gray-50 dark:bg-slate-700/60 p-6 rounded-2xl w-32 md:w-48 h-32 md:h-48 shrink-0"
                >
                    <iconify-icon
                        icon={`circle-flags:${country.country_code.toLowerCase()}`}
                        style="font-size: 120px;"
                    ></iconify-icon>
                </div>
                <div class="md:text-left text-center">
                    <h1
                        class="mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-6xl tracking-tight"
                    >
                        {country.country_name}
                    </h1>
                    <p
                        class="max-w-2xl text-gray-600 dark:text-cyan-300/80 text-xl leading-relaxed"
                    >
                        Discover {country.statistics.total_beans} coffee beans from
                        {country.statistics.total_regions} distinct regions across
                        {country.country_name}.
                    </p>
                </div>
            </div>

            <!-- Quick Stats Grid -->
            <div class="gap-4 grid grid-cols-2 lg:grid-cols-4 mb-8">
                <div
                    class="bg-orange-50/50 dark:bg-emerald-500/5 p-4 border border-orange-100 dark:border-emerald-500/20 rounded-xl text-center"
                >
                    <div
                        class="mb-1 font-bold text-orange-600 dark:text-emerald-400 text-3xl"
                    >
                        {country.statistics.total_beans.toLocaleString()}
                    </div>
                    <div
                        class="font-medium text-gray-600 dark:text-cyan-400/70 text-xs uppercase tracking-wider"
                    >
                        Coffee Beans
                    </div>
                </div>
                <div
                    class="bg-blue-50/50 dark:bg-blue-500/5 p-4 border border-blue-100 dark:border-blue-500/20 rounded-xl text-center"
                >
                    <div
                        class="mb-1 font-bold text-blue-600 dark:text-cyan-400 text-3xl"
                    >
                        {country.statistics.total_regions}
                    </div>
                    <div
                        class="font-medium text-gray-600 dark:text-cyan-400/70 text-xs uppercase tracking-wider"
                    >
                        Regions
                    </div>
                </div>
                <div
                    class="bg-purple-50/50 dark:bg-purple-500/5 p-4 border border-purple-100 dark:border-purple-500/20 rounded-xl text-center"
                >
                    <div
                        class="mb-1 font-bold text-purple-600 dark:text-purple-400 text-3xl"
                    >
                        {country.statistics.total_farms}
                    </div>
                    <div
                        class="font-medium text-gray-600 dark:text-cyan-400/70 text-xs uppercase tracking-wider"
                    >
                        Farms
                    </div>
                </div>
                <div
                    class="bg-amber-50/50 dark:bg-amber-500/5 p-4 border border-amber-100 dark:border-amber-500/20 rounded-xl text-center"
                >
                    <div
                        class="mb-1 font-bold text-amber-600 dark:text-amber-400 text-3xl"
                    >
                        {country.statistics.avg_elevation
                            ? `${Math.round(country.statistics.avg_elevation)}m`
                            : "N/A"}
                    </div>
                    <div
                        class="font-medium text-gray-600 dark:text-cyan-400/70 text-xs uppercase tracking-wider"
                    >
                        Avg Elevation
                    </div>
                </div>
            </div>

            <!-- Detailed Insights -->
            <div class="gap-6 grid md:grid-cols-3">
                <!-- Varietals -->
                {#if varietalItems.length > 0}
                    <InsightCard
                        title="Common Varietals"
                        icon={Leaf}
                        items={varietalItems}
                        variant="blue"
                    />
                {/if}

                <!-- Processing Distribution -->
                {#if processItems.length > 0}
                    <InsightCard
                        title="Processing Methods"
                        icon={Droplets}
                        items={processItems}
                        variant="orange"
                    />
                {/if}

                <!-- Common Tasting Notes -->
                {#if noteItems.length > 0}
                    <InsightCard
                        title="Common Tasting Notes"
                        icon={TrendingUp}
                        items={noteItems}
                        variant="purple"
                    />
                {/if}
            </div>
        </div>

        <!-- Regions Section -->
        <div class="mb-12">
            <div
                class="flex md:flex-row flex-col md:items-end justify-between gap-6 mb-8"
            >
                <div>
                    <h2
                        class="font-bold text-gray-900 dark:text-cyan-100 text-3xl"
                    >
                        Coffee Regions
                    </h2>
                    <p class="mt-1 text-gray-600 dark:text-cyan-400/80">
                        Explore {country.statistics.total_regions} regions in {country.country_name}
                    </p>
                </div>

                <!-- Search Bar -->
                <div class="relative w-full max-w-md">
                    <Search
                        class="top-1/2 left-3 absolute -translate-y-1/2 w-4 h-4 text-gray-500 dark:text-cyan-400/70"
                    />
                    <Input
                        bind:value={searchQuery}
                        placeholder="Search regions in this country..."
                        class="bg-white dark:bg-slate-700/60 pl-10 border-gray-200 dark:border-slate-600 focus:border-orange-500 dark:focus:border-emerald-500 text-gray-900 dark:text-cyan-200 focus:ring-orange-500 dark:focus:ring-emerald-500/50"
                    />
                </div>
            </div>

            {#if filteredRegions.length > 0}
                <div
                    class="gap-4 sm:gap-6 grid grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
                >
                    {#each filteredRegions as region, i (region.region_name)}
                        <div in:scale|global={{ delay: (i % 20) * 30 }}>
                            <RegionCard
                                {region}
                                countryCode={country.country_code}
                            />
                        </div>
                    {/each}
                </div>
            {:else}
                <div
                    class="py-20 rounded-2xl border-2 border-gray-100 dark:border-slate-800 border-dashed text-center"
                >
                    <MapPin
                        class="mx-auto mb-4 w-12 h-12 text-gray-300 dark:text-slate-700"
                    />
                    <h3
                        class="mb-2 font-semibold text-gray-900 dark:text-cyan-100 text-xl"
                    >
                        No regions found
                    </h3>
                    <p class="text-gray-600 dark:text-cyan-400/70">
                        No matching coffee regions found for "{searchQuery}".
                    </p>
                </div>
            {/if}
        </div>
    {/if}
</div>
