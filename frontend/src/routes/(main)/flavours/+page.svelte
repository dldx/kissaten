<script lang="ts">
    import type { PageData } from './$types';
    import TastingNoteCategoryCard from '$lib/components/TastingNoteCategoryCard.svelte';
    import SunburstChart from '$lib/components/SunburstChart.svelte';
    import Scene from '$lib/components/flavours/Scene.svelte';
    import SearchFilters from '$lib/components/search/SearchFilters.svelte';
    import { flavourImageUrl, flavourImageDimensions } from '$lib/stores/flavourImageStore';
    import { getCategoryEmoji } from '$lib/utils';
    import { transformToSunburstData } from '$lib/utils/sunburstDataTransform';
    import * as d3 from 'd3';
    import type { SunburstData } from '$lib/types/sunburst';
    import { goto } from '$app/navigation';
    import { browser } from '$app/environment';
    import { page } from '$app/stores';
    import { Filter, Search } from 'lucide-svelte';
    import { Input } from "$lib/components/ui/input/index.js";

    let { data }: { data: PageData } = $props();

    // State for loading and filtered data - initialize immediately with server data
    let isLoading = $state(false);
    let serverFilteredCategories = $state(data.categories);
    let serverFilteredMetadata = $state(data.metadata);

    // Now we can safely derive from the initialized state
    const categories = $derived(serverFilteredCategories);
    const metadata = $derived(serverFilteredMetadata);

    // Original search functionality for tasting notes (client-side)
    let searchQuery = $state('');

    // Advanced filter state variables - initialize from URL parameters
    let advancedSearchQuery = $state(data.filterParams.searchQuery);
    let tastingNotesQuery = $state(data.filterParams.tastingNotesQuery);
    let roasterFilter = $state(data.filterParams.roasterFilter);
    let roasterLocationFilter = $state(data.filterParams.roasterLocationFilter);
    let originFilter = $state(data.filterParams.originFilter);
    let roastLevelFilter = $state(data.filterParams.roastLevelFilter);
    let roastProfileFilter = $state(data.filterParams.roastProfileFilter);
    let processFilter = $state(data.filterParams.processFilter);
    let varietyFilter = $state(data.filterParams.varietyFilter);
    let minPrice = $state(data.filterParams.minPrice);
    let maxPrice = $state(data.filterParams.maxPrice);
    let minWeight = $state(data.filterParams.minWeight);
    let maxWeight = $state(data.filterParams.maxWeight);
    let minElevation = $state(data.filterParams.minElevation);
    let maxElevation = $state(data.filterParams.maxElevation);
    let regionFilter = $state(data.filterParams.regionFilter);
    let producerFilter = $state(data.filterParams.producerFilter);
    let farmFilter = $state(data.filterParams.farmFilter);
    let inStockOnly = $state(data.filterParams.inStockOnly);
    let isDecaf = $state(data.filterParams.isDecaf);
    let isSingleOrigin = $state(data.filterParams.isSingleOrigin);
    let sortBy = $state('relevance');
    let sortOrder = $state('desc');

    // Filter visibility state
    let showAdvancedFilters = $state(false);

    // Check if any advanced filters are active
    const hasActiveFilters = $derived(
        advancedSearchQuery ||
        tastingNotesQuery ||
        roasterFilter.length > 0 ||
        roasterLocationFilter.length > 0 ||
        originFilter.length > 0 ||
        roastLevelFilter ||
        roastProfileFilter ||
        processFilter ||
        varietyFilter ||
        minPrice ||
        maxPrice ||
        minWeight ||
        maxWeight ||
        minElevation ||
        maxElevation ||
        regionFilter ||
        producerFilter ||
        farmFilter ||
        inStockOnly ||
        isDecaf !== undefined ||
        isSingleOrigin !== undefined
    );

    // View toggle
    let showSunburst = $state(false);

    // Generate search page URL with current filter parameters
    const searchPageUrl = $derived.by(() => {
        const params = new URLSearchParams();

        // Add parameters only if they have values
        if (advancedSearchQuery) params.set('q', advancedSearchQuery);
        if (tastingNotesQuery) params.set('tasting_notes_query', tastingNotesQuery);
        if (roasterFilter.length > 0) roasterFilter.forEach(r => params.append('roaster', r));
        if (roasterLocationFilter.length > 0) roasterLocationFilter.forEach(rl => params.append('roaster_location', rl));
        if (originFilter.length > 0) originFilter.forEach(o => params.append('origin', o));
        if (regionFilter) params.set('region', regionFilter);
        if (producerFilter) params.set('producer', producerFilter);
        if (farmFilter) params.set('farm', farmFilter);
        if (roastLevelFilter) params.set('roast_level', roastLevelFilter);
        if (roastProfileFilter) params.set('roast_profile', roastProfileFilter);
        if (processFilter) params.set('process', processFilter);
        if (varietyFilter) params.set('variety', varietyFilter);
        if (minPrice) params.set('min_price', minPrice);
        if (maxPrice) params.set('max_price', maxPrice);
        if (minWeight) params.set('min_weight', minWeight);
        if (maxWeight) params.set('max_weight', maxWeight);
        if (minElevation) params.set('min_elevation', minElevation);
        if (maxElevation) params.set('max_elevation', maxElevation);
        if (inStockOnly) params.set('in_stock_only', 'true');
        if (isDecaf !== undefined) params.set('is_decaf', isDecaf.toString());
        if (isSingleOrigin !== undefined) params.set('is_single_origin', isSingleOrigin.toString());

        return params.toString() ? `/search?${params.toString()}` : '/search';
    });

    // Client-side API call function
    async function fetchFilteredData() {
        if (!browser) return;

        isLoading = true;

        try {
            // Build API URL with parameters
            const apiUrl = new URL('/api/v1/tasting-note-categories', $page.url.origin);

            // Add parameters to API URL if they exist
            if (advancedSearchQuery) apiUrl.searchParams.set('query', advancedSearchQuery);
            if (tastingNotesQuery) apiUrl.searchParams.set('tasting_notes_query', tastingNotesQuery);
            if (roasterFilter.length > 0) roasterFilter.forEach(r => apiUrl.searchParams.append('roaster', r));
            if (roasterLocationFilter.length > 0) roasterLocationFilter.forEach(rl => apiUrl.searchParams.append('roaster_location', rl));
            if (originFilter.length > 0) originFilter.forEach(o => apiUrl.searchParams.append('origin', o));
            if (regionFilter) apiUrl.searchParams.set('region', regionFilter);
            if (producerFilter) apiUrl.searchParams.set('producer', producerFilter);
            if (farmFilter) apiUrl.searchParams.set('farm', farmFilter);
            if (roastLevelFilter) apiUrl.searchParams.set('roast_level', roastLevelFilter);
            if (roastProfileFilter) apiUrl.searchParams.set('roast_profile', roastProfileFilter);
            if (processFilter) apiUrl.searchParams.set('process', processFilter);
            if (varietyFilter) apiUrl.searchParams.set('variety', varietyFilter);
            if (minPrice) apiUrl.searchParams.set('min_price', minPrice);
            if (maxPrice) apiUrl.searchParams.set('max_price', maxPrice);
            if (minWeight) apiUrl.searchParams.set('min_weight', minWeight);
            if (maxWeight) apiUrl.searchParams.set('max_weight', maxWeight);
            if (minElevation) apiUrl.searchParams.set('min_elevation', minElevation);
            if (maxElevation) apiUrl.searchParams.set('max_elevation', maxElevation);
            if (inStockOnly) apiUrl.searchParams.set('in_stock_only', 'true');
            if (isDecaf !== undefined) apiUrl.searchParams.set('is_decaf', isDecaf.toString());
            if (isSingleOrigin !== undefined) apiUrl.searchParams.set('is_single_origin', isSingleOrigin.toString());

            const response = await fetch(apiUrl.toString());

            if (!response.ok) {
                throw new Error('Failed to fetch filtered data');
            }

            const result = await response.json();

            if (result.success) {
                const { categories, metadata } = result.data;

                // Sort subcategories within each primary category by note count
                for (const primaryKey in categories) {
                    categories[primaryKey].sort((a: any, b: any) => (b.note_count || 0) - (a.note_count || 0));
                }

                serverFilteredCategories = categories;
                serverFilteredMetadata = metadata;
            }
        } catch (error) {
            console.error('Error fetching filtered data:', error);
            // Fallback to original data on error
            serverFilteredCategories = data.categories;
            serverFilteredMetadata = data.metadata;
        } finally {
            isLoading = false;
        }
    }

    // Search and filter functions
    async function performAdvancedSearch() {
        if (!browser) return;

        const params = new URLSearchParams();

        // Add parameters only if they have values
        if (advancedSearchQuery) params.set('q', advancedSearchQuery);
        if (tastingNotesQuery) params.set('tasting_notes_query', tastingNotesQuery);
        if (roasterFilter.length > 0) roasterFilter.forEach(r => params.append('roaster', r));
        if (roasterLocationFilter.length > 0) roasterLocationFilter.forEach(rl => params.append('roaster_location', rl));
        if (originFilter.length > 0) originFilter.forEach(o => params.append('origin', o));
        if (regionFilter) params.set('region', regionFilter);
        if (producerFilter) params.set('producer', producerFilter);
        if (farmFilter) params.set('farm', farmFilter);
        if (roastLevelFilter) params.set('roast_level', roastLevelFilter);
        if (roastProfileFilter) params.set('roast_profile', roastProfileFilter);
        if (processFilter) params.set('process', processFilter);
        if (varietyFilter) params.set('variety', varietyFilter);
        if (minPrice) params.set('min_price', minPrice);
        if (maxPrice) params.set('max_price', maxPrice);
        if (minWeight) params.set('min_weight', minWeight);
        if (maxWeight) params.set('max_weight', maxWeight);
        if (minElevation) params.set('min_elevation', minElevation);
        if (maxElevation) params.set('max_elevation', maxElevation);
        if (inStockOnly) params.set('in_stock_only', 'true');
        if (isDecaf !== undefined) params.set('is_decaf', isDecaf.toString());
        if (isSingleOrigin !== undefined) params.set('is_single_origin', isSingleOrigin.toString());

        // Update URL without navigation (for bookmarking/sharing)
        const url = params.toString() ? `/flavours?${params.toString()}` : '/flavours';
        history.replaceState({}, '', url);

        // Fetch filtered data client-side
        await fetchFilteredData();
    }

    async function clearAdvancedFilters() {
        if (!browser) return;

        // Reset all advanced filter state
        advancedSearchQuery = '';
        tastingNotesQuery = '';
        roasterFilter = [];
        roasterLocationFilter = [];
        originFilter = [];
        roastLevelFilter = '';
        roastProfileFilter = '';
        processFilter = '';
        varietyFilter = '';
        minPrice = '';
        maxPrice = '';
        minWeight = '';
        maxWeight = '';
        minElevation = '';
        maxElevation = '';
        regionFilter = '';
        producerFilter = '';
        farmFilter = '';
        inStockOnly = false;
        isDecaf = undefined;
        isSingleOrigin = undefined;

        // Update URL without navigation
        history.replaceState({}, '', '/flavours');

        // Reset to original data
        serverFilteredCategories = data.categories;
        serverFilteredMetadata = data.metadata;
    }

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
        <h2 class="process-category-title-shadow mb-6 font-bold text-gray-900 text-2xl text-center process-category-title-dark">
            Understanding Tasting Notes
        </h2>
        <div class="gap-6 grid md:grid-cols-2 lg:grid-cols-3 text-gray-700 text-sm">
            <div class="bg-white {$flavourImageUrl ? 'supports-[backdrop-filter]:bg-background/60' : ''} process-card-shadow p-6 rounded-lg process-card-dark">
                <h3 class="process-info-title-shadow mb-3 font-semibold text-gray-900 process-category-title-dark">🎯 Origin Impact</h3>
                <p class="process-page-description-dark">
                    The soil, climate, and altitude where coffee grows dramatically influences its flavor.
                    Ethiopian coffees often show floral notes, while Colombian beans may have nutty characteristics.
                </p>
            </div>
            <div class="bg-white {$flavourImageUrl ? 'supports-[backdrop-filter]:bg-background/60' : ''} process-card-shadow p-6 rounded-lg process-card-dark">
                <h3 class="process-info-title-shadow mb-3 font-semibold text-gray-900 process-category-title-dark">🔥 Processing Methods</h3>
                <p class="process-page-description-dark">
                    How the coffee cherry is processed affects flavor development.
                    Natural processing often creates fruity notes, while washed processing highlights acidity and clarity.
                </p>
            </div>
            <div class="bg-white {$flavourImageUrl ? 'supports-[backdrop-filter]:bg-background/60' : ''} process-card-shadow p-6 rounded-lg process-card-dark">
                <h3 class="process-info-title-shadow mb-3 font-semibold text-gray-900 process-category-title-dark">⏰ Roast Development</h3>
                <p class="process-page-description-dark">
                    Roasting time and temperature create different flavor compounds.
                    Light roasts preserve origin characteristics, while darker roasts develop caramelized and roasted flavors.
                </p>
            </div>
            <div class="bg-white {$flavourImageUrl ? 'supports-[backdrop-filter]:bg-background/60' : ''} process-card-shadow p-6 rounded-lg process-card-dark">
                <h3 class="process-info-title-shadow mb-3 font-semibold text-gray-900 process-category-title-dark">🌱 Variety Influence</h3>
                <p class="process-page-description-dark">
                    Different coffee varieties have distinct flavor potentials.
                    Geisha varieties often show floral and tea-like qualities, while Bourbon varieties may be sweet and balanced.
                </p>
            </div>
            <div class="bg-white {$flavourImageUrl ? 'supports-[backdrop-filter]:bg-background/60' : ''} process-card-shadow p-6 rounded-lg process-card-dark">
                <h3 class="process-info-title-shadow mb-3 font-semibold text-gray-900 process-category-title-dark">👨‍🍳 Brewing Impact</h3>
                <p class="process-page-description-dark">
                    Your brewing method affects which flavors are extracted.
                    Pour-over methods highlight acidity and brightness, while espresso emphasizes body and sweetness.
                </p>
            </div>
        </div>

    </div>



    <!-- Main Content Area with Sidebar Layout -->
    <div class="flex lg:flex-row flex-col gap-2 lg:gap-8">
        <!-- Advanced Filters Sidebar -->
        {#if showAdvancedFilters}
            <div class="w-full lg:w-fit">
                <div class="bg-white {$flavourImageUrl ? 'supports-[backdrop-filter]:bg-background/60' : ''} dark:bg-slate-800/60 shadow-lg p-6 border border-gray-200 dark:border-cyan-500/30 rounded-xl">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="font-semibold text-gray-900 dark:text-cyan-100 text-lg">Advanced Filters</h3>
                        <button
                            onclick={() => showAdvancedFilters = false}
                            class="text-gray-400 hover:text-gray-600 dark:hover:text-cyan-300 dark:text-cyan-400/70"
                            aria-label="Close advanced filters"
                        >
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>

                    <SearchFilters
                        bind:searchQuery={advancedSearchQuery}
                        bind:tastingNotesQuery={tastingNotesQuery}
                        bind:roasterFilter={roasterFilter}
                        bind:roasterLocationFilter={roasterLocationFilter}
                        bind:originFilter={originFilter}
                        bind:roastLevelFilter={roastLevelFilter}
                        bind:roastProfileFilter={roastProfileFilter}
                        bind:processFilter={processFilter}
                        bind:varietyFilter={varietyFilter}
                        bind:minPrice={minPrice}
                        bind:maxPrice={maxPrice}
                        bind:minWeight={minWeight}
                        bind:maxWeight={maxWeight}
                        bind:minElevation={minElevation}
                        bind:maxElevation={maxElevation}
                        bind:regionFilter={regionFilter}
                        bind:producerFilter={producerFilter}
                        bind:farmFilter={farmFilter}
                        bind:inStockOnly={inStockOnly}
                        bind:isDecaf={isDecaf}
                        bind:isSingleOrigin={isSingleOrigin}
                        bind:sortBy={sortBy}
                        bind:sortOrder={sortOrder}
                        bind:showFilters={showAdvancedFilters}
                        originOptions={data.originOptions}
                        allRoasters={data.allRoasters}
                        roasterLocationOptions={data.roasterLocationOptions}
                        onSearch={performAdvancedSearch}
                        onClearFilters={clearAdvancedFilters}
                    />

                    <!-- Link to search page with current filters -->
                    {#if hasActiveFilters}
                        <div class="mt-4 pt-4 border-gray-200 dark:border-slate-600 border-t">
                            <a
                                href={searchPageUrl}
                                class="flex justify-center items-center gap-2 bg-orange-500 hover:bg-orange-600 dark:bg-emerald-600 dark:hover:bg-emerald-700 px-4 py-2.5 rounded-lg w-full font-medium text-white transition-colors"
                            >
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                </svg>
                                View Matching Coffee Beans
                            </a>
                            <p class="mt-2 text-gray-500 dark:text-cyan-400/70 text-xs text-center">
                                See actual coffee beans with these tasting notes
                            </p>
                        </div>
                    {/if}
                </div>
            </div>
        {/if}

        <!-- Main Content -->
        <div class="flex-1">
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
            <!-- Search Bar and Advanced Filters -->
    <div class="mx-auto mb-8 max-w-md">
        <div class="flex items-center gap-2">
            <!-- Original Search Bar -->
            <div class="relative flex-1">
                <Search class="top-1/2 left-3 absolute w-4 h-4 text-gray-500 dark:text-cyan-400/70 -translate-y-1/2 transform" />
                <Input
                    bind:value={searchQuery}
                    placeholder="Search tasting notes, categories..."
                    class="bg-white dark:bg-slate-700/60 pl-10 border-gray-200 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 focus:ring-orange-500 dark:focus:ring-emerald-500/50 text-gray-900 dark:placeholder:text-cyan-400/70 dark:text-cyan-200 placeholder:text-gray-500"
                />
            </div>

            <!-- Advanced Filters Toggle Button -->
            <button
                onclick={() => showAdvancedFilters = !showAdvancedFilters}
                class="relative bg-white dark:bg-slate-700/60 hover:bg-gray-50 dark:hover:bg-slate-600/80 p-3 border border-gray-300 dark:border-slate-600 rounded-xl transition-colors {showAdvancedFilters ? 'ring-2 ring-orange-500 dark:ring-emerald-500/50' : ''} {hasActiveFilters ? 'border-orange-500 dark:border-emerald-500' : ''}"
                title="Advanced Filters"
                aria-label="Toggle advanced filters"
            >
                <Filter class="w-4 h-4 text-gray-600 dark:text-cyan-300 {hasActiveFilters ? 'text-orange-600 dark:text-emerald-400' : ''}" />
                {#if hasActiveFilters}
                    <div class="top-0 right-0 absolute bg-orange-500 dark:bg-emerald-500 rounded-full w-2 h-2 -translate-y-1 translate-x-1 transform"></div>
                {/if}
            </button>
        </div>

        {#if isLoading}
            <div class="flex justify-center items-center mt-4 text-gray-500 dark:text-cyan-400/80">
                <div class="flex items-center gap-2">
                    <div class="border-2 border-gray-300 dark:border-cyan-400/30 border-t-gray-600 dark:border-t-cyan-400 rounded-full w-4 h-4 animate-spin"></div>
                    <span class="text-sm">Filtering tasting notes...</span>
                </div>
            </div>
        {:else if searchQuery && categories && Object.keys(categories).length === 0}
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
                <div class="sticky top-16 bg-white {$flavourImageUrl ? 'supports-[backdrop-filter]:bg-background/60' : ''} dark:bg-slate-800/60 shadow-lg mx-auto p-4 border border-gray-200 dark:border-cyan-500/30 rounded-xl max-w-8xl z-10">
                    <div class="mb-4 text-gray-500 dark:text-cyan-400/70 text-sm text-center">
                        <p>Hover over segments to see details. Click to explore further.</p>
                    </div>

                    <div class="w-full max-h-[70vh] aspect-square">
                        {#if filteredSunburstData.children && filteredSunburstData.children.length > 0}
                            <SunburstChart
                                data={filteredSunburstData}
                                className="w-full h-full"
                            />
                        {:else}
                            <div
                                class="flex justify-center items-center w-full h-full text-gray-500 dark:text-cyan-400/80"
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

        </div>
    </div>
</div>