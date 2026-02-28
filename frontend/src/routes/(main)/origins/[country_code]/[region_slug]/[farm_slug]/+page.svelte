<script lang="ts">
    import type { PageData } from "./$types";
    import GeographyBreadcrumb from "$lib/components/GeographyBreadcrumb.svelte";
    import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
    import {
        User,
        MapPin,
        ArrowUpCircle,
        Coffee,
        Warehouse,
        Grape,
        Droplets,
        Leaf,
        TrendingUp,
    } from "lucide-svelte";
    import { scale } from "svelte/transition";
    import { api } from "$lib/api";
    import { getProcessIcon } from "$lib/utils";

    import InsightCard from "$lib/components/InsightCard.svelte";
    import ElevationMountainChart from "$lib/components/ElevationMountainChart.svelte";

    let { data }: { data: PageData } = $props();
    const farm = $derived(data.farm);

    // Prepare items for InsightCard
    const varietalItems = $derived(
        farm?.varietals?.slice(0, 5).map((v) => ({
            label: v.variety,
            count: v.count,
            href: `/search?variety="${encodeURIComponent(v.variety)}"&region=${encodeURIComponent(farm.region_name)}&origin=${farm.country_code}&farm=${encodeURIComponent(farm.farm_name)}`,
        })) || [],
    );

    const processItems = $derived(
        farm?.processing_methods
            ?.filter((m) => !m.process.toLowerCase().includes("unknown"))
            .slice(0, 5)
            .map((m) => ({
                label: m.process,
                count: m.count,
                icon: getProcessIcon(m.process),
                href: `/search?process="${encodeURIComponent(m.process)}"&region=${encodeURIComponent(farm.region_name)}&origin=${farm.country_code}&farm=${encodeURIComponent(farm.farm_name)}`,
            })) || [],
    );

    const noteItems = $derived(
        farm?.common_tasting_notes?.slice(0, 5).map((n) => ({
            label: n.note,
            count: n.frequency,
            href: `/search?tasting_notes_query="${encodeURIComponent(n.note)}"&region=${encodeURIComponent(farm.region_name)}&origin=${farm.country_code}&farm=${encodeURIComponent(farm.farm_name)}`,
        })) || [],
    );
</script>

<svelte:head>
    <title>{farm?.farm_name} - {farm?.region_name} - Kissaten</title>
</svelte:head>

<div class="mx-auto px-4 py-8 max-w-7xl container">
    <GeographyBreadcrumb
        countryCode={farm?.country_code}
        countryName={farm?.country_name}
        regionName={farm?.region_name}
        farmName={farm?.farm_name}
    />

    {#if farm}
        <!-- Header Section -->
        <div
            class="bg-white dark:bg-slate-800/80 shadow-sm mb-8 p-8 border border-gray-200 dark:border-slate-700 rounded-xl"
        >
            <div
                class="flex md:flex-row flex-col justify-between md:items-start gap-6 mb-8"
            >
                <div>
                    <div class="flex items-center gap-3 mb-3">
                        <iconify-icon
                            icon={`circle-flags:${farm.country_code.toLowerCase()}`}
                            class="text-xl"
                        ></iconify-icon>
                        <span
                            class="font-medium text-gray-500 dark:text-cyan-400/70 text-sm uppercase tracking-wider"
                        >
                            {farm.region_name}, {farm.country_name}
                        </span>
                    </div>
                    <div class="flex flex-col gap-2">
                        <h1
                            class="font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl tracking-tight"
                        >
                            {farm.farm_name}
                        </h1>
                        <div
                            class="flex flex-wrap items-center gap-x-4 gap-y-2 mt-2"
                        >
                            {#each farm.producers.filter((producer) => producer.name.length > 0) as producer}
                                <div
                                    class="group flex items-center gap-2 min-w-0 text-gray-600 dark:text-cyan-300/80 text-lg"
                                    title={`${producer.mention_count} mention${producer.mention_count !== 1 ? "s" : ""}`}
                                >
                                    <User class="w-5 h-5 shrink-0" />
                                    <span
                                        class="flex items-center min-w-0 dark:group-hover:text-cyan-100 group-hover:text-gray-900 transition-colors"
                                    >
                                        <span class="truncate"
                                            >{producer.name}</span
                                        >
                                        {#if farm.producers.filter((producer) => producer.name.length > 0).length > 1}
                                            <span
                                                class="ml-1 text-gray-400 dark:text-cyan-500/50 text-sm shrink-0"
                                            >
                                                ({producer.mention_count})
                                            </span>
                                        {/if}
                                    </span>
                                </div>
                            {/each}
                        </div>
                    </div>
                </div>

                <div class="flex flex-col gap-3 md:min-w-[45%] md:max-w-[55%]">
                    {#if farm.beans.length > 0}
                        <ElevationMountainChart
                            beans={farm.beans}
                            farmElevationMin={farm.elevation_min}
                            farmElevationMax={farm.elevation_max}
                        />
                    {/if}
                    <div class="flex flex-wrap justify-center gap-3">
                        {#if farm.elevation_min || farm.elevation_max}
                            <div
                                class="flex items-center gap-2 bg-orange-50 dark:bg-emerald-500/10 px-4 py-2 border border-orange-100 dark:border-emerald-500/20 rounded-lg text-orange-700 dark:text-emerald-300"
                            >
                                <ArrowUpCircle class="w-4 h-4" />
                                <span class="font-medium">
                                    {#if !farm.elevation_min || !farm.elevation_max || farm.elevation_min === farm.elevation_max}
                                        {farm.elevation_min || farm.elevation_max}m
                                    {:else}
                                        {farm.elevation_min} - {farm.elevation_max}m
                                    {/if}
                                </span>
                            </div>
                        {/if}
                        <div
                            class="flex items-center gap-2 bg-blue-50 dark:bg-blue-500/10 px-4 py-2 border border-blue-100 dark:border-blue-500/20 rounded-lg text-blue-700 dark:text-blue-300"
                        >
                            <Coffee class="w-4 h-4" />
                            <span class="font-medium"
                                >{farm.beans.length} Coffee{farm.beans.length === 1
                                    ? ""
                                    : "s"}</span
                            >
                        </div>
                    </div>
                </div>
            </div>

            <!-- Detailed Insights -->
            <div class="gap-6 grid md:grid-cols-3">
                <!-- Cultivated Varietals -->
                {#if varietalItems.length > 0}
                    <InsightCard
                        title="Common Varietals"
                        icon={Leaf}
                        items={varietalItems}
                        variant="blue"
                    />
                {/if}

                <!-- Processing Methods -->
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

        <!-- Associated Beans Section -->
        <div>
            <h2
                class="mb-6 font-bold text-gray-900 dark:text-cyan-100 text-3xl"
            >
                Coffee from {farm.farm_name}
            </h2>

            <div
                class="gap-4 sm:gap-6 grid grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
            >
                {#each farm.beans as bean, i (bean.id)}
                    <div in:scale|global={{ delay: (i % 20) * 30 }}>
                        <a
                            href={"/roasters" + bean.bean_url_path}
                            class="block"
                        >
                            <CoffeeBeanCard {bean} />
                        </a>
                    </div>
                {/each}
            </div>
        </div>
    {/if}
</div>
