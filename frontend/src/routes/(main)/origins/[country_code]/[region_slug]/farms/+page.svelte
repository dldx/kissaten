<script lang="ts">
    import type { PageData } from "./$types";
    import GeographyBreadcrumb from "$lib/components/GeographyBreadcrumb.svelte";
    import FarmCard from "$lib/components/FarmCard.svelte";
    import { Input } from "$lib/components/ui/input/index.js";
    import { Search, Warehouse } from "lucide-svelte";
    import { scale } from "svelte/transition";

    let { data }: { data: PageData } = $props();
    const region = $derived(data.region);
    const farms = $derived(data.farms);

    let searchQuery = $state("");
    let filteredFarms = $derived(
        searchQuery.trim()
            ? farms.filter((f) =>
                  f.farm_name.toLowerCase().includes(searchQuery.toLowerCase()),
              )
            : farms,
    );
</script>

<svelte:head>
    <title>Farms in {region?.region_name} - Kissaten</title>
</svelte:head>

<div class="mx-auto px-4 py-8 max-w-7xl container">
    <GeographyBreadcrumb
        countryCode={region?.country_code}
        countryName={region?.country_name}
        regionName={region?.region_name}
    />

    <div class="mb-12">
        <h1
            class="mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl tracking-tight"
        >
            Coffee Farms in {region?.region_name}
        </h1>
        <p class="max-w-3xl text-gray-600 dark:text-cyan-300/80 text-lg">
            Discover {farms.length} dedicated coffee producers and farms across the
            {region?.region_name} region of {region?.country_name}.
        </p>
    </div>

    <!-- Search Bar -->
    <div class="relative max-w-md mb-8">
        <Search
            class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 dark:text-cyan-400/70"
        />
        <Input
            bind:value={searchQuery}
            placeholder="Search farms..."
            class="pl-10 bg-white dark:bg-slate-700/60 border-gray-200 dark:border-slate-600 focus:border-orange-500 dark:focus:border-emerald-500 focus:ring-orange-500 dark:focus:ring-emerald-500/50 text-gray-900 dark:text-cyan-200"
        />
    </div>

    {#if filteredFarms.length > 0}
        <div
            class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 mb-8"
        >
            {#each filteredFarms as farm, i (farm.farm_name)}
                <div in:scale|global={{ delay: (i % 20) * 30 }}>
                    <FarmCard
                        {farm}
                        countryCode={region.country_code}
                        regionSlug={data.regionSlug}
                    />
                </div>
            {/each}
        </div>
    {:else}
        <div
            class="py-20 text-center border-2 border-dashed border-gray-100 dark:border-slate-800 rounded-2xl"
        >
            <Warehouse
                class="mx-auto w-12 h-12 text-gray-300 dark:text-slate-700 mb-4"
            />
            <h3
                class="text-xl font-semibold text-gray-900 dark:text-cyan-100 mb-2"
            >
                No farms found
            </h3>
            <p class="text-gray-600 dark:text-cyan-400/70">
                No matching coffee farms found for "{searchQuery}".
            </p>
        </div>
    {/if}
</div>
