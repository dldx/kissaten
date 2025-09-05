<script lang="ts">
    import type { PageData } from './$types';
    import TastingNoteCategoryCard from '$lib/components/TastingNoteCategoryCard.svelte';

    let { data }: { data: PageData } = $props();

    const categories = $derived(data.categories);
    const metadata = $derived(data.metadata);

    // Search functionality
    let searchQuery = $state('');

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
                const filteredData = data.filter(subcategory => {
                    // Check if secondary category matches
                    const secondaryMatches = subcategory.secondary_category?.toLowerCase().includes(query);

                    // Check if any tasting notes match
                    const notesMatch = subcategory.tasting_notes?.some(note =>
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


    // Calculate filtered metadata
    const filteredMetadata = $derived.by(() => {
        const categories = filteredCategories;
        const totalNotes = categories.reduce((sum, { data }) =>
            sum + data.reduce((subSum, sub) => subSum + (sub.note_count || 0), 0), 0
        );

        const totalUniqueDescriptors = Array.from(new Set(
            categories.flatMap(({ data }) =>
                data.flatMap(sub => sub.tasting_notes || [])
            )
        )).length;

        return {
            total_notes: totalNotes,
            total_unique_descriptors: totalUniqueDescriptors,
            total_primary_categories: categories.length
        };
    });

    // Calculate global maximum bean count across all tasting notes
    const globalMaxBeanCount = $derived.by(() => {
        const allBeanCounts = sortedCategories
            .flatMap(({ data }) => data)
            .flatMap(sub => sub.tasting_notes_with_counts || [])
            .map(note => note.bean_count);

        return allBeanCounts.length > 0 ? Math.max(...allBeanCounts) : 1;
    });
</script>

<svelte:head>
    <title>Coffee Tasting Notes - Kissaten</title>
    <meta name="description" content="Explore the diverse flavor profiles found in specialty coffee. From fruity and floral to nutty and chocolatey notes." />
</svelte:head>

<div class="mx-auto px-4 py-8 max-w-7xl container">
    <!-- Header -->
    <div class="mb-12 text-center">
        <h1 class="varietal-title-shadow mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl">
            Coffee Tasting Notes
        </h1>
        <p class="varietal-description-shadow mx-auto mb-6 max-w-3xl text-gray-600 dark:text-cyan-300/80 text-xl">
            Explore the diverse flavor profiles found in specialty coffee. Each note has been categorized
            to help you discover patterns and understand the complexity of coffee flavors.
        </p>
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

    <!-- Tasting Note Categories Grid -->
    <div class="space-y-6">
        {#each filteredCategories as { key, data }}
            <TastingNoteCategoryCard
                primaryCategory={key}
                subcategories={data}
                searchQuery={searchQuery}
                globalMaxBeanCount={globalMaxBeanCount}
            />
        {/each}

        {#if filteredCategories.length === 0 && !searchQuery}
            <div class="py-12 text-center">
                <p class="text-gray-500 dark:text-cyan-400/80 text-lg">No tasting note categories available.</p>
            </div>
        {/if}
    </div>

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