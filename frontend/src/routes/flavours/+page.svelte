<script lang="ts">
    import type { PageData } from './$types';
    import TastingNoteCategoryCard from '$lib/components/TastingNoteCategoryCard.svelte';

    let { data }: { data: PageData } = $props();

    const categories = $derived(data.categories);
    const metadata = $derived(data.metadata);

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
</script>

<svelte:head>
    <title>Coffee Tasting Notes - Kissaten</title>
    <meta name="description" content="Explore the diverse flavor profiles found in specialty coffee. From fruity and floral to nutty and chocolatey notes." />
</svelte:head>

<div class="mx-auto px-4 py-8 max-w-7xl container">
    <!-- Header -->
    <div class="mb-12 text-center">
        <h1 class="mb-4 font-bold text-gray-900 text-4xl md:text-5xl">
            Coffee Tasting Notes
        </h1>
        <p class="mx-auto mb-6 max-w-3xl text-gray-600 text-xl">
            Explore the diverse flavor profiles found in specialty coffee. Each note has been categorized
            to help you discover patterns and understand the complexity of coffee flavors.
        </p>
        <div class="bg-orange-50 mx-auto p-4 border border-orange-200 rounded-lg max-w-md">
            <p class="font-medium text-orange-800">
                {metadata?.total_notes?.toLocaleString() || 0} notes • {metadata?.total_unique_descriptors?.toLocaleString() || 0} unique descriptors • {metadata?.total_primary_categories || 0} categories
            </p>
        </div>
    </div>

    <!-- Tasting Note Categories Grid -->
    <div class="space-y-6">
        {#each sortedCategories as { key, data }}
            <TastingNoteCategoryCard
                primaryCategory={key}
                subcategories={data}
            />
        {/each}
    </div>

    <!-- Additional Info Section -->
    <div class="bg-gray-50 mt-16 p-8 rounded-xl">
        <h2 class="mb-6 font-bold text-gray-900 text-2xl text-center">
            Understanding Tasting Notes
        </h2>
        <div class="gap-6 grid md:grid-cols-2 lg:grid-cols-3 text-gray-700 text-sm">
            <div class="bg-white p-6 rounded-lg">
                <h3 class="mb-3 font-semibold text-gray-900">🎯 Origin Impact</h3>
                <p>
                    The soil, climate, and altitude where coffee grows dramatically influences its flavor.
                    Ethiopian coffees often show floral notes, while Colombian beans may have nutty characteristics.
                </p>
            </div>
            <div class="bg-white p-6 rounded-lg">
                <h3 class="mb-3 font-semibold text-gray-900">🔥 Processing Methods</h3>
                <p>
                    How the coffee cherry is processed affects flavor development.
                    Natural processing often creates fruity notes, while washed processing highlights acidity and clarity.
                </p>
            </div>
            <div class="bg-white p-6 rounded-lg">
                <h3 class="mb-3 font-semibold text-gray-900">⏰ Roast Development</h3>
                <p>
                    Roasting time and temperature create different flavor compounds.
                    Light roasts preserve origin characteristics, while darker roasts develop caramelized and roasted flavors.
                </p>
            </div>
            <div class="bg-white p-6 rounded-lg">
                <h3 class="mb-3 font-semibold text-gray-900">🌱 Variety Influence</h3>
                <p>
                    Different coffee varieties have distinct flavor potentials.
                    Geisha varieties often show floral and tea-like qualities, while Bourbon varieties may be sweet and balanced.
                </p>
            </div>
            <div class="bg-white p-6 rounded-lg">
                <h3 class="mb-3 font-semibold text-gray-900">👨‍🍳 Brewing Impact</h3>
                <p>
                    Your brewing method affects which flavors are extracted.
                    Pour-over methods highlight acidity and brightness, while espresso emphasizes body and sweetness.
                </p>
            </div>
        </div>
    </div>
</div>