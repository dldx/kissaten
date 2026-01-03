<script lang="ts">
    import type { PageData } from "./$types";
    import GeographyBreadcrumb from "$lib/components/GeographyBreadcrumb.svelte";
    import RegionCard from "$lib/components/RegionCard.svelte";
    import { Input } from "$lib/components/ui/input/index.js";
    import { Search, MapPin } from "lucide-svelte";
    import { scale } from "svelte/transition";

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
</script>

<svelte:head>
    <title>Regions in {country?.country_name} - Kissaten</title>
</svelte:head>

<div class="mx-auto px-4 py-8 max-w-7xl container">
    <GeographyBreadcrumb
        countryCode={country?.country_code}
        countryName={country?.country_name}
    />

    <div class="mb-12">
        <h1
            class="mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl tracking-tight"
        >
            Coffee Regions in {country?.country_name}
        </h1>
        <p class="max-w-3xl text-gray-600 dark:text-cyan-300/80 text-lg">
            Explore the {regions.length} distinct geographical regions producing exceptional
            coffee across {country?.country_name}.
        </p>
    </div>

    <!-- Search Bar -->
    <div class="relative max-w-md mb-8">
        <Search
            class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 dark:text-cyan-400/70"
        />
        <Input
            bind:value={searchQuery}
            placeholder="Search regions..."
            class="pl-10 bg-white dark:bg-slate-700/60 border-gray-200 dark:border-slate-600 focus:border-orange-500 dark:focus:border-emerald-500 focus:ring-orange-500 dark:focus:ring-emerald-500/50 text-gray-900 dark:text-cyan-200"
        />
    </div>

    {#if filteredRegions.length > 0}
        <div
            class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 mb-8"
        >
            {#each filteredRegions as region, i (region.region_name)}
                <div in:scale|global={{ delay: (i % 20) * 30 }}>
                    <RegionCard {region} countryCode={country.country_code} />
                </div>
            {/each}
        </div>
    {:else}
        <div
            class="py-20 text-center border-2 border-dashed border-gray-100 dark:border-slate-800 rounded-2xl"
        >
            <MapPin
                class="mx-auto w-12 h-12 text-gray-300 dark:text-slate-700 mb-4"
            />
            <h3
                class="text-xl font-semibold text-gray-900 dark:text-cyan-100 mb-2"
            >
                No regions found
            </h3>
            <p class="text-gray-600 dark:text-cyan-400/70">
                No matching coffee regions found for "{searchQuery}".
            </p>
        </div>
    {/if}
</div>
