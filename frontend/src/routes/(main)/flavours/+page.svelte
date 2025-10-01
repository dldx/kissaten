<script lang="ts">
    import type { PageData } from './$types';
    import TastingNoteCategoryCard from '$lib/components/TastingNoteCategoryCard.svelte';
    import SunburstChart from '$lib/components/SunburstChart.svelte';
    import Scene from '$lib/components/flavours/Scene.svelte';
    import { flavourImageUrl, flavourImageDimensions } from '$lib/stores/flavourImageStore';
    import { getCategoryEmoji } from '$lib/utils';
    import { transformToSunburstData } from '$lib/utils/sunburstDataTransform';
    import * as d3 from 'd3';
    import type { SunburstData } from '$lib/types/sunburst';

    let { data }: { data: PageData } = $props();

    const categories = $derived(data.categories);
    const metadata = $derived(data.metadata);

    // Search functionality
    let searchQuery = $state('');

    // View toggle
    let showSunburst = $state(false);

    // Define the order we want to display categories (roughly by frequency/importance)
    const categoryOrder = [
        'Fruity',
        'Cocoa',
        'Nutty',
        'Sweet',
        'Floral',
        'Roasted',
        'Spicy',
        'Earthy',
        'Sour/Fermented',
        'Green/Vegetative',
        'Alcohol/Fermented',
        'Chemical',
        'Papery/Musty',
        'Other'
    ];


    // Sort categories by our defined order, then by total notes
    const sortedCategories = $derived(
        categoryOrder
            .map(categoryKey => ({
                key: categoryKey,
                data: categories[categoryKey] || []
            }))
            .filter(({ data }) => data.length > 0)
            .concat(
                // Add any categories not in our predefined order
                Object.keys(categories)
                    .filter(key => !categoryOrder.includes(key))
                    .map(categoryKey => ({
                        key: categoryKey,
                        data: categories[categoryKey] || []
                    }))
                    .filter(({ data }) => data.length > 0)
            )
    );

    // Filter categories based on search query
    const filteredCategories = $derived.by(() => {
        if (!searchQuery.trim()) {
            return sortedCategories;
        }

        const query = searchQuery.toLowerCase().trim();

        return sortedCategories
            .map(({ key, data }) => {
                // Check if primary category matches
                const primaryMatches = key.toLowerCase().includes(query);

                // Filter subcategories that match the search
                const filteredData = data.filter((subcategory: any) => {
                    // Check if secondary category matches
                    const secondaryMatches = subcategory.secondary_category?.toLowerCase().includes(query);

                    // Check if any tasting notes match
                    const notesMatch = subcategory.tasting_notes?.some((note: string) =>
                        note.toLowerCase().includes(query)
                    );

                    return primaryMatches || secondaryMatches || notesMatch;
                });

                return {
                    key,
                    data: filteredData
                };
            })
            .filter(({ data }) => data.length > 0);
    });


    // Calculate global maximum bean count across all tasting notes
    const globalMaxBeanCount = $derived.by(() => {
        const allBeanCounts = sortedCategories
            .flatMap(({ data }) => data)
            .flatMap(sub => sub.tasting_notes_with_counts || [])
            .map(note => note.bean_count);

        return allBeanCounts.length > 0 ? Math.max(...allBeanCounts) : 1;
    });

    // Transform data for sunburst chart
    const sunburstData = $derived.by(() => {
        return transformToSunburstData(categories);
    });

    // Filtered data for the Sunburst chart
    const filteredSunburstData = $derived.by(() => {
        const query = searchQuery.toLowerCase().trim();
        if (!query) {
            return sunburstData;
        }

        // Function to recursively filter the sunburst data
        function filter(node: SunburstData): SunburstData | null {
            if (!node) return null;

            // If the node itself matches, we want to keep it and all its children
            if (node.name.toLowerCase().includes(query)) {
                return node;
            }

            // If it has children, filter them
            if (node.children) {
                const filteredChildren = node.children
                    .map(filter)
                    .filter((n) => n !== null) as SunburstData[];

                if (filteredChildren.length > 0) {
                    // Create a new node with the filtered children
                    // and recalculate its value if it exists
                    const newNode = { ...node, children: filteredChildren };
                    if (newNode.value !== undefined) {
                        newNode.value = d3.sum(filteredChildren, (d) => d.value || 0);
                    }
                    return newNode;
                }
            }

            return null;
        }

        const filtered = filter(sunburstData);

        // If the root is filtered out, return a default structure
        return filtered || { name: 'Tasting Notes', children: [] };
    });
</script>

<svelte:head>
    <title>Coffee Tasting Notes - Kissaten</title>
    <meta name="description" content="Explore the diverse flavor profiles found in specialty coffee. From fruity and floral to nutty and chocolatey notes." />
</svelte:head>

    <div class="top-0 left-0 z-0 fixed w-full h-full">
{#if $flavourImageUrl}
<!-- {#key $flavourImageDimensions.width + $flavourImageUrl } -->
{#key $flavourImageUrl }
        <!-- <Scene imageUrl={$flavourImageUrl} /> -->
         <img src={$flavourImageUrl} alt="Flavour Image" class="w-full h-full object-cover" />
{/key}
<!-- {/key} -->
{/if}
    </div>

<div class="z-10 relative mx-auto px-4 py-8 max-w-7xl container">
    <!-- Header -->
    <div class="mb-12 text-center">
        <h1 class="varietal-title-shadow mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl">
            Coffee Tasting Notes
        </h1>
        <p class="varietal-description-shadow mx-auto mb-6 max-w-3xl text-gray-600 dark:text-cyan-300/80 text-xl">
            Explore the diverse flavor profiles found in specialty coffee. Each note has been categorized
            to help you discover patterns and understand the complexity of coffee flavors.
        </p>

        <!-- View Toggle -->
        <div class="flex justify-center mb-8">
            <div class="bg-gray-100 dark:bg-slate-700/60 p-1 border border-gray-200 dark:border-slate-600 rounded-lg">
                <button
                    onclick={() => showSunburst = false}
                    class="px-4 py-2 text-sm font-medium rounded-md transition-colors {showSunburst
                        ? 'text-gray-500 dark:text-gray-400'
                        : 'bg-white dark:bg-slate-600 text-gray-900 dark:text-cyan-100 shadow-sm'}">
                    📋 List View
                </button>
                <button
                    onclick={() => showSunburst = true}
                    class="px-4 py-2 text-sm font-medium rounded-md transition-colors {showSunburst
                        ? 'bg-white dark:bg-slate-600 text-gray-900 dark:text-cyan-100 shadow-sm'
                        : 'text-gray-500 dark:text-gray-400'}">
                    🎯 Sunburst Chart
                </button>
            </div>
        </div>
    </div>
        <!-- Search Bar -->
        <div class="mx-auto mb-8 max-w-2xl">
            <div class="relative">
                <input
                    type="text"
                    bind:value={searchQuery}
                    placeholder="Search tasting notes, categories, or flavors..."
                    class="bg-white dark:bg-slate-700/60 px-4 py-3 pl-12 border border-gray-300 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 rounded-xl focus:ring-2 focus:ring-orange-500 dark:focus:ring-emerald-500/50 w-full text-gray-900 dark:placeholder:text-cyan-400/70 dark:text-cyan-200 placeholder:text-gray-500 text-lg"
                />
                <div class="top-1/2 left-4 absolute text-gray-400 dark:text-cyan-400/70 -translate-y-1/2 transform">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                </div>
                {#if searchQuery}
                    <button
                        onclick={() => searchQuery = ''}
                        aria-label="Clear search"
                        class="top-1/2 right-4 absolute text-gray-400 hover:text-gray-600 dark:hover:text-cyan-300 dark:text-cyan-400/70 -translate-y-1/2 transform"
                    >
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                {/if}
            </div>
            {#if searchQuery && filteredCategories.length === 0}
                <p class="mt-4 text-gray-500 dark:text-cyan-400/80 text-center">
                    No tasting notes found matching "{searchQuery}". Try a different search term.
                </p>
            {/if}
        </div>

    {#if !showSunburst}
        <!-- Category Anchor Links -->
        <nav class="flex flex-wrap justify-center gap-2 mb-10">
            {#each filteredCategories as { key }}
                <a href={`#category-${key.replace(/[^a-zA-Z0-9]/g, '-')}`}
                   class="bg-orange-100 hover:bg-orange-200 dark:bg-cyan-900/40 dark:hover:bg-cyan-700/60 px-3 py-1 border border-orange-200 dark:border-cyan-700/40 rounded font-medium text-orange-800 dark:text-cyan-200 text-sm transition-colors">
                    {getCategoryEmoji(key)} {key}
                </a>
            {/each}
        </nav>

        <!-- Tasting Note Categories Grid -->
        <div class="space-y-6">
            {#each filteredCategories as { key, data }}
                <!-- Group subcategories by secondary_category -->
                {@const grouped = (() => {
                    const map = new Map();
                    for (const sub of data) {
                        const sec = sub.secondary_category || 'General';
                        if (!map.has(sec)) map.set(sec, []);
                        map.get(sec).push(sub);
                    }
                    return Array.from(map.entries());
                })()}
                <div id={`category-${key.replace(/[^a-zA-Z0-9]/g, '-')}`}
                     class="bg-white {$flavourImageUrl ? 'supports-[backdrop-filter]:bg-background/60' : ''} dark:bg-slate-800/60 shadow-sm hover:shadow-md dark:hover:shadow-cyan-500/20 dark:shadow-cyan-500/10 p-6 border border-gray-200 dark:border-cyan-500/30 rounded-xl transition-shadow scroll-mt-24">
                    <h2 class="flex items-center gap-2 mb-2 font-semibold text-gray-900 dark:text-cyan-100 text-2xl">
                        <a href={`#category-${key.replace(/[^a-zA-Z0-9]/g, '-')}`}
                           class="px-1 rounded focus:outline-none focus:ring-2 focus:ring-orange-400 decoration-dotted hover:underline"
                           title="Link to {key}">
                            {getCategoryEmoji(key)} {key}
                        </a>
                    </h2>
                    <div class="space-y-4 ml-2">
                        {#each grouped as [secondary, subs]}
                            <TastingNoteCategoryCard
                                primaryCategory={key}
                                secondaryCategory={secondary}
                                subcategories={subs}
                                searchQuery={searchQuery}
                                globalMaxBeanCount={globalMaxBeanCount}
                            />
                        {/each}
                    </div>
                </div>
            {/each}

            {#if filteredCategories.length === 0 && !searchQuery}
                <div class="py-12 text-center">
                    <p class="text-gray-500 dark:text-cyan-400/80 text-lg">No tasting note categories available.</p>
                </div>
            {/if}
        </div>
    {:else}
        <!-- Sunburst Chart Section -->
        <div class="bg-white {$flavourImageUrl ? 'supports-[backdrop-filter]:bg-background/60' : ''} dark:bg-slate-800/60 shadow-sm mx-auto p-2 border border-gray-200 dark:border-cyan-500/30 rounded-xl w-[90vw] md:w-[80%] h-[100vw] md:h-[90%]">
            <div class="text-gray-500 dark:text-cyan-400/70 text-sm text-center">
                <p>Hover over segments to see details. Click to explore further.</p>
            </div>

            <div class="flex justify-center">
                {#if filteredSunburstData.children && filteredSunburstData.children.length > 0}
                    <SunburstChart
                        data={filteredSunburstData}
                        width={800}
                        height={800}
                        className="w-[100%] h-[100%]"
                    />
                {:else}
                    <div
                        class="flex justify-center items-center h-96 text-gray-500 dark:text-cyan-400/80"
                    >
                        <div class="text-center">
                            <div class="mb-4 text-4xl">📊</div>
                            <p class="text-lg">No tasting note data available</p>
                            <p class="text-sm">Try refreshing the page or check back later</p>
                        </div>
                    </div>
                {/if}
            </div>

        </div>
    {/if}

    <!-- Additional Info Section -->
    <div class="bg-gray-50 dark:bg-slate-800/60 mt-16 p-8 border dark:border-cyan-500/30 rounded-xl">
        <h2 class="mb-6 font-bold text-gray-900 dark:text-cyan-100 text-2xl text-center">
            Understanding Tasting Notes
        </h2>
        <div class="gap-6 grid md:grid-cols-2 lg:grid-cols-3 text-gray-700 dark:text-cyan-300/80 text-sm">
            <div class="bg-white dark:bg-slate-700/50 p-6 border dark:border-slate-600/50 rounded-lg">
                <h3 class="mb-3 font-semibold text-gray-900 dark:text-emerald-300">🎯 Origin Impact</h3>
                <p>
                    The soil, climate, and altitude where coffee grows dramatically influences its flavor.
                    Ethiopian coffees often show floral notes, while Colombian beans may have nutty characteristics.
                </p>
            </div>
            <div class="bg-white dark:bg-slate-700/50 p-6 border dark:border-slate-600/50 rounded-lg">
                <h3 class="mb-3 font-semibold text-gray-900 dark:text-emerald-300">🔥 Processing Methods</h3>
                <p>
                    How the coffee cherry is processed affects flavor development.
                    Natural processing often creates fruity notes, while washed processing highlights acidity and clarity.
                </p>
            </div>
            <div class="bg-white dark:bg-slate-700/50 p-6 border dark:border-slate-600/50 rounded-lg">
                <h3 class="mb-3 font-semibold text-gray-900 dark:text-emerald-300">⏰ Roast Development</h3>
                <p>
                    Roasting time and temperature create different flavor compounds.
                    Light roasts preserve origin characteristics, while darker roasts develop caramelized and roasted flavors.
                </p>
            </div>
            <div class="bg-white dark:bg-slate-700/50 p-6 border dark:border-slate-600/50 rounded-lg">
                <h3 class="mb-3 font-semibold text-gray-900 dark:text-emerald-300">🌱 Variety Influence</h3>
                <p>
                    Different coffee varieties have distinct flavor potentials.
                    Geisha varieties often show floral and tea-like qualities, while Bourbon varieties may be sweet and balanced.
                </p>
            </div>
            <div class="bg-white dark:bg-slate-700/50 p-6 border dark:border-slate-600/50 rounded-lg">
                <h3 class="mb-3 font-semibold text-gray-900 dark:text-emerald-300">👨‍🍳 Brewing Impact</h3>
                <p>
                    Your brewing method affects which flavors are extracted.
                    Pour-over methods highlight acidity and brightness, while espresso emphasizes body and sweetness.
                </p>
            </div>
        </div>
    </div>
</div>