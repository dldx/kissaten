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

    let { data }: { data: PageData } = $props();
    const farm = $derived(data.farm);
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
            class="bg-white dark:bg-slate-800/80 mb-8 p-8 border border-gray-200 dark:border-slate-700 rounded-xl shadow-sm"
        >
            <div
                class="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8"
            >
                <div>
                    <div class="flex items-center gap-3 mb-3">
                        <iconify-icon
                            icon={`circle-flags:${farm.country_code.toLowerCase()}`}
                            class="text-xl"
                        ></iconify-icon>
                        <span
                            class="text-gray-500 dark:text-cyan-400/70 font-medium uppercase tracking-wider text-sm"
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
                            {#each farm.producers as producer}
                                <div
                                    class="flex items-center gap-2 text-gray-600 dark:text-cyan-300/80 text-lg group"
                                    title={`${producer.mention_count} mention${producer.mention_count !== 1 ? "s" : ""}`}
                                >
                                    <User class="w-5 h-5" />
                                    <span
                                        class="group-hover:text-gray-900 dark:group-hover:text-cyan-100 transition-colors"
                                    >
                                        {producer.name}
                                        {#if farm.producers.length > 1}
                                            <span
                                                class="ml-1 text-gray-400 dark:text-cyan-500/50 text-sm"
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

                <div class="flex flex-wrap gap-3">
                    {#if farm.elevation_min || farm.elevation_max}
                        <div
                            class="flex items-center gap-2 bg-orange-50 dark:bg-emerald-500/10 text-orange-700 dark:text-emerald-300 px-4 py-2 rounded-lg border border-orange-100 dark:border-emerald-500/20"
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
                        class="flex items-center gap-2 bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-300 px-4 py-2 rounded-lg border border-blue-100 dark:border-blue-500/20"
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

            <!-- Detailed Insights -->
            <div class="gap-6 grid md:grid-cols-3">
                <!-- Cultivated Varietals -->
                {#if farm.varietals && farm.varietals.length > 0}
                    <div
                        class="bg-gray-50 p-6 border border-blue-200 rounded-lg varietal-detail-insight-card-blue"
                    >
                        <div
                            class="flex items-center gap-2 mb-4 text-blue-600 dark:text-cyan-400"
                        >
                            <Leaf class="w-5 h-5" />
                            <h3
                                class="varietal-detail-insight-title-shadow font-semibold text-blue-900 dark:text-cyan-200"
                            >
                                Common Varietals
                            </h3>
                        </div>
                        <div class="space-y-1">
                            {#each farm.varietals.slice(0, 5) as varietal}
                                <a
                                    href={`/varietals/${api.normalizeVarietalName(varietal.variety)}`}
                                    class="flex justify-between items-center hover:bg-accent p-1 px-2 rounded text-sm transition-colors"
                                >
                                    <span
                                        class="varietal-detail-insight-item-shadow text-blue-800 dark:text-cyan-300 truncate"
                                    >
                                        {varietal.variety}
                                    </span>
                                    <span
                                        class="varietal-detail-insight-item-shadow font-medium text-blue-900 dark:text-cyan-200"
                                    >
                                        {varietal.count} bean{varietal.count !==
                                        1
                                            ? "s"
                                            : ""}
                                    </span>
                                </a>
                            {/each}
                        </div>
                    </div>
                {/if}

                <!-- Processing Methods -->
                {#if farm.processing_methods && farm.processing_methods.length > 0}
                    <div
                        class="bg-gray-50 p-6 border border-orange-200 rounded-lg varietal-detail-insight-card-orange"
                    >
                        <div
                            class="flex items-center gap-2 mb-4 text-orange-600 dark:text-orange-400"
                        >
                            <Droplets class="w-5 h-5" />
                            <h3
                                class="varietal-detail-insight-title-shadow font-semibold text-orange-900 dark:text-orange-200"
                            >
                                Processing Methods
                            </h3>
                        </div>
                        <div class="space-y-1">
                            {#each farm.processing_methods
                                .filter((method) => !method.process
                                            .toLowerCase()
                                            .includes("unknown"))
                                .slice(0, 5) as method}
                                {@const Icon = getProcessIcon(method.process)}
                                <a
                                    href={`/processes/${api.normalizeProcessName(method.process)}`}
                                    class="flex justify-between items-center hover:bg-accent p-1 px-2 rounded text-sm transition-colors"
                                >
                                    <span
                                        class="flex items-center gap-2 varietal-detail-insight-item-shadow text-orange-800 dark:text-orange-300 truncate"
                                    >
                                        <Icon class="w-3.5 h-3.5" />
                                        {method.process}
                                    </span>
                                    <span
                                        class="varietal-detail-insight-item-shadow font-medium text-orange-900 dark:text-orange-200"
                                    >
                                        {method.count} bean{method.count !== 1
                                            ? "s"
                                            : ""}
                                    </span>
                                </a>
                            {/each}
                        </div>
                    </div>
                {/if}

                <!-- Common Tasting Notes -->
                {#if farm.common_tasting_notes && farm.common_tasting_notes.length > 0}
                    <div
                        class="bg-gray-50 p-6 border border-purple-200 rounded-lg varietal-detail-insight-card-purple"
                    >
                        <div
                            class="flex items-center gap-2 mb-4 text-purple-600 dark:text-purple-400"
                        >
                            <TrendingUp class="w-5 h-5" />
                            <h3
                                class="varietal-detail-insight-title-shadow font-semibold text-purple-900 dark:text-purple-200"
                            >
                                Common Tasting Notes
                            </h3>
                        </div>
                        <div class="space-y-1">
                            {#each farm.common_tasting_notes.slice(0, 5) as note}
                                <a
                                    href={`/search?tasting_notes_query="${encodeURIComponent(note.note)}"&region=${api.normalizeRegionName(farm.region_name)}&country=${farm.country_code}&farm=${api.normalizeFarmName(farm.farm_name)}`}
                                    class="flex justify-between items-center hover:bg-accent p-1 px-2 rounded text-sm transition-colors"
                                >
                                    <span
                                        class="varietal-detail-insight-item-shadow text-purple-800 dark:text-purple-300 truncate"
                                    >
                                        {note.note}
                                    </span>
                                    <span
                                        class="varietal-detail-insight-item-shadow font-medium text-purple-900 dark:text-purple-200"
                                    >
                                        {note.frequency} bean{note.frequency !==
                                        1
                                            ? "s"
                                            : ""}
                                    </span>
                                </a>
                            {/each}
                        </div>
                    </div>
                {/if}
            </div>
        </div>

        <!-- Associated Beans Section -->
        <div>
            <h2
                class="font-bold text-gray-900 dark:text-cyan-100 text-3xl mb-6"
            >
                Coffee from {farm.farm_name}
            </h2>

            <div
                class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
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
