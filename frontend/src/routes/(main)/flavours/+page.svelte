<script lang="ts">
    import type { PageData } from "./$types";
    import TastingNoteCategoryCard from "$lib/components/TastingNoteCategoryCard.svelte";
    import SunburstChart from "$lib/components/SunburstChart.svelte";
    import Scene from "$lib/components/flavours/Scene.svelte";
    import SearchFilters from "$lib/components/search/SearchFilters.svelte";
    import {
        flavourImageUrl,
        flavourImageDimensions,
        flavourImageAttribution,
    } from "$lib/stores/flavourImageStore";
    import { flavourImagesEnabled } from "$lib/stores/settingsStore";
    import { getCategoryEmoji } from "$lib/utils";
    import { transformToSunburstData } from "$lib/utils/sunburstDataTransform";
    import * as d3 from "d3";
    import type { SunburstData } from "$lib/types/sunburst";
    import { goto } from "$app/navigation";
    import { browser } from "$app/environment";
    import { page } from "$app/state";
    import { Coffee, Filter, Search } from "lucide-svelte";
    import { Input } from "$lib/components/ui/input/index.js";
    import { Button } from "$lib/components/ui/button/index.js";
    import { onMount } from "svelte";
    import { Switch } from "$lib/components/ui/switch";
    import { Label } from "$lib/components/ui/label";
    import { List, Target } from "lucide-svelte";
    let { data }: { data: PageData } = $props();

    onMount(() => {
        $flavourImageUrl = null;
        $flavourImageAttribution = null;
        if(window.innerWidth < 768) {
            $flavourImagesEnabled = false;
        }
    });

    // Clear flavour image when experiments are disabled
    $effect(() => {
        if (!$flavourImagesEnabled) {
            $flavourImageUrl = null;
            $flavourImageAttribution = null;
        }
    });

    // State for loading and filtered data - initialize immediately with server data
    let isLoading = $state(false);
    let serverFilteredCategories = $state(data.categories);
    let serverFilteredMetadata = $state(data.metadata);

    // Now we can safely derive from the initialized state
    const categories = $derived(serverFilteredCategories);
    const metadata = $derived(serverFilteredMetadata);

    // Original search functionality for tasting notes (client-side)
    let searchQuery = $state("");

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
    let sortBy = $state("relevance");
    let sortOrder = $state("desc");

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
            isSingleOrigin !== undefined,
    );

    // View toggle
    let showSunburst = $state(false);

    // Generate search page URL with current filter parameters
    const searchPageUrl = $derived.by(() => {
        const params = new URLSearchParams();

        // Add parameters only if they have values
        if (advancedSearchQuery) params.set("q", advancedSearchQuery);
        if (tastingNotesQuery)
            params.set("tasting_notes_query", tastingNotesQuery);
        if (roasterFilter.length > 0)
            roasterFilter.forEach((r) => params.append("roaster", r));
        if (roasterLocationFilter.length > 0)
            roasterLocationFilter.forEach((rl) =>
                params.append("roaster_location", rl),
            );
        if (originFilter.length > 0)
            originFilter.forEach((o) => params.append("origin", o));
        if (regionFilter) params.set("region", regionFilter);
        if (producerFilter) params.set("producer", producerFilter);
        if (farmFilter) params.set("farm", farmFilter);
        if (roastLevelFilter) params.set("roast_level", roastLevelFilter);
        if (roastProfileFilter) params.set("roast_profile", roastProfileFilter);
        if (processFilter) params.set("process", processFilter);
        if (varietyFilter) params.set("variety", varietyFilter);
        if (minPrice) params.set("min_price", minPrice);
        if (maxPrice) params.set("max_price", maxPrice);
        if (minWeight) params.set("min_weight", minWeight);
        if (maxWeight) params.set("max_weight", maxWeight);
        if (minElevation) params.set("min_elevation", minElevation);
        if (maxElevation) params.set("max_elevation", maxElevation);
        if (inStockOnly) params.set("in_stock_only", "true");
        if (isDecaf !== undefined) params.set("is_decaf", isDecaf.toString());
        if (isSingleOrigin !== undefined)
            params.set("is_single_origin", isSingleOrigin.toString());

        return params.toString() ? `/search?${params.toString()}` : "/search";
    });

    // Reactive bean count that updates when filter values change
    const totalBeanCount = $derived.by(async () => {
        if (!browser) return 0;

        // Only fetch if there are active filters
        if (!hasActiveFilters) return 0;

        try {
            // Build API URL with parameters for search endpoint (just to get count)
            const searchUrl = new URL("/api/v1/search", page.url.origin);
            searchUrl.searchParams.set("per_page", "1"); // We only need the count, not the results

            // Add parameters to search URL if they exist
            if (advancedSearchQuery)
                searchUrl.searchParams.set("query", advancedSearchQuery);
            if (tastingNotesQuery)
                searchUrl.searchParams.set(
                    "tasting_notes_query",
                    tastingNotesQuery,
                );
            if (roasterFilter.length > 0)
                roasterFilter.forEach((r) =>
                    searchUrl.searchParams.append("roaster", r),
                );
            if (roasterLocationFilter.length > 0)
                roasterLocationFilter.forEach((rl) =>
                    searchUrl.searchParams.append("roaster_location", rl),
                );
            if (originFilter.length > 0)
                originFilter.forEach((o) =>
                    searchUrl.searchParams.append("origin", o),
                );
            if (regionFilter)
                searchUrl.searchParams.set("region", regionFilter);
            if (producerFilter)
                searchUrl.searchParams.set("producer", producerFilter);
            if (farmFilter) searchUrl.searchParams.set("farm", farmFilter);
            if (roastLevelFilter)
                searchUrl.searchParams.set("roast_level", roastLevelFilter);
            if (roastProfileFilter)
                searchUrl.searchParams.set("roast_profile", roastProfileFilter);
            if (processFilter)
                searchUrl.searchParams.set("process", processFilter);
            if (varietyFilter)
                searchUrl.searchParams.set("variety", varietyFilter);
            if (minPrice) searchUrl.searchParams.set("min_price", minPrice);
            if (maxPrice) searchUrl.searchParams.set("max_price", maxPrice);
            if (minWeight) searchUrl.searchParams.set("min_weight", minWeight);
            if (maxWeight) searchUrl.searchParams.set("max_weight", maxWeight);
            if (minElevation)
                searchUrl.searchParams.set("min_elevation", minElevation);
            if (maxElevation)
                searchUrl.searchParams.set("max_elevation", maxElevation);
            if (inStockOnly)
                searchUrl.searchParams.set("in_stock_only", "true");
            if (isDecaf !== undefined)
                searchUrl.searchParams.set("is_decaf", isDecaf.toString());
            if (isSingleOrigin !== undefined)
                searchUrl.searchParams.set(
                    "is_single_origin",
                    isSingleOrigin.toString(),
                );

            const response = await fetch(searchUrl.toString());

            if (!response.ok) {
                throw new Error("Failed to fetch bean count");
            }

            const result = await response.json();

            if (result.success && result.metadata) {
                return result.metadata.total_results || 0;
            }
            return 0;
        } catch (error) {
            console.error("Error fetching bean count:", error);
            return 0;
        }
    });

    // Client-side API call function
    async function fetchFilteredData() {
        if (!browser) return;

        isLoading = true;

        try {
            // Build API URL with parameters
            const apiUrl = new URL(
                "/api/v1/tasting-note-categories",
                page.url.origin,
            );

            // Add parameters to API URL if they exist
            if (advancedSearchQuery)
                apiUrl.searchParams.set("query", advancedSearchQuery);
            if (tastingNotesQuery)
                apiUrl.searchParams.set(
                    "tasting_notes_query",
                    tastingNotesQuery,
                );
            if (roasterFilter.length > 0)
                roasterFilter.forEach((r) =>
                    apiUrl.searchParams.append("roaster", r),
                );
            if (roasterLocationFilter.length > 0)
                roasterLocationFilter.forEach((rl) =>
                    apiUrl.searchParams.append("roaster_location", rl),
                );
            if (originFilter.length > 0)
                originFilter.forEach((o) =>
                    apiUrl.searchParams.append("origin", o),
                );
            if (regionFilter) apiUrl.searchParams.set("region", regionFilter);
            if (producerFilter)
                apiUrl.searchParams.set("producer", producerFilter);
            if (farmFilter) apiUrl.searchParams.set("farm", farmFilter);
            if (roastLevelFilter)
                apiUrl.searchParams.set("roast_level", roastLevelFilter);
            if (roastProfileFilter)
                apiUrl.searchParams.set("roast_profile", roastProfileFilter);
            if (processFilter)
                apiUrl.searchParams.set("process", processFilter);
            if (varietyFilter)
                apiUrl.searchParams.set("variety", varietyFilter);
            if (minPrice) apiUrl.searchParams.set("min_price", minPrice);
            if (maxPrice) apiUrl.searchParams.set("max_price", maxPrice);
            if (minWeight) apiUrl.searchParams.set("min_weight", minWeight);
            if (maxWeight) apiUrl.searchParams.set("max_weight", maxWeight);
            if (minElevation)
                apiUrl.searchParams.set("min_elevation", minElevation);
            if (maxElevation)
                apiUrl.searchParams.set("max_elevation", maxElevation);
            if (inStockOnly) apiUrl.searchParams.set("in_stock_only", "true");
            if (isDecaf !== undefined)
                apiUrl.searchParams.set("is_decaf", isDecaf.toString());
            if (isSingleOrigin !== undefined)
                apiUrl.searchParams.set(
                    "is_single_origin",
                    isSingleOrigin.toString(),
                );

            const response = await fetch(apiUrl.toString());

            if (!response.ok) {
                throw new Error("Failed to fetch filtered data");
            }

            const result = await response.json();

            if (result.success) {
                const { categories, metadata } = result.data;

                // Sort subcategories within each primary category by note count
                for (const primaryKey in categories) {
                    categories[primaryKey].sort(
                        (a: any, b: any) =>
                            (b.note_count || 0) - (a.note_count || 0),
                    );
                }

                serverFilteredCategories = categories;
                serverFilteredMetadata = metadata;
            }
        } catch (error) {
            console.error("Error fetching filtered data:", error);
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
        if (advancedSearchQuery) params.set("q", advancedSearchQuery);
        if (tastingNotesQuery)
            params.set("tasting_notes_query", tastingNotesQuery);
        if (roasterFilter.length > 0)
            roasterFilter.forEach((r) => params.append("roaster", r));
        if (roasterLocationFilter.length > 0)
            roasterLocationFilter.forEach((rl) =>
                params.append("roaster_location", rl),
            );
        if (originFilter.length > 0)
            originFilter.forEach((o) => params.append("origin", o));
        if (regionFilter) params.set("region", regionFilter);
        if (producerFilter) params.set("producer", producerFilter);
        if (farmFilter) params.set("farm", farmFilter);
        if (roastLevelFilter) params.set("roast_level", roastLevelFilter);
        if (roastProfileFilter) params.set("roast_profile", roastProfileFilter);
        if (processFilter) params.set("process", processFilter);
        if (varietyFilter) params.set("variety", varietyFilter);
        if (minPrice) params.set("min_price", minPrice);
        if (maxPrice) params.set("max_price", maxPrice);
        if (minWeight) params.set("min_weight", minWeight);
        if (maxWeight) params.set("max_weight", maxWeight);
        if (minElevation) params.set("min_elevation", minElevation);
        if (maxElevation) params.set("max_elevation", maxElevation);
        if (inStockOnly) params.set("in_stock_only", "true");
        if (isDecaf !== undefined) params.set("is_decaf", isDecaf.toString());
        if (isSingleOrigin !== undefined)
            params.set("is_single_origin", isSingleOrigin.toString());

        // Update URL without navigation (for bookmarking/sharing)
        const url = params.toString()
            ? `/flavours?${params.toString()}`
            : "/flavours";
        goto(url, { replaceState: true, noScroll: true });

        // Fetch filtered data client-side
        await fetchFilteredData();
    }

    async function clearAdvancedFilters() {
        if (!browser) return;

        // Reset all advanced filter state
        advancedSearchQuery = "";
        tastingNotesQuery = "";
        roasterFilter = [];
        roasterLocationFilter = [];
        originFilter = [];
        roastLevelFilter = "";
        roastProfileFilter = "";
        processFilter = "";
        varietyFilter = "";
        minPrice = "";
        maxPrice = "";
        minWeight = "";
        maxWeight = "";
        minElevation = "";
        maxElevation = "";
        regionFilter = "";
        producerFilter = "";
        farmFilter = "";
        inStockOnly = false;
        isDecaf = undefined;
        isSingleOrigin = undefined;

        // Update URL without navigation
        goto("/flavours", { replaceState: true, noScroll: true });

        // Reset to original data
        serverFilteredCategories = data.categories;
        serverFilteredMetadata = data.metadata;
    }

    // Define the order we want to display categories (roughly by frequency/importance)
    const categoryOrder = [
        "Fruity",
        "Cocoa",
        "Nutty",
        "Sweet",
        "Floral",
        "Roasted",
        "Spicy",
        "Earthy",
        "Sour/Fermented",
        "Green/Vegetative",
        "Alcohol/Fermented",
        "Chemical",
        "Papery/Musty",
        "Other",
    ];

    // Sort categories by our defined order, then by total notes
    const sortedCategories = $derived(
        categoryOrder
            .map((categoryKey) => ({
                key: categoryKey,
                data: categories[categoryKey] || [],
            }))
            .filter(({ data }) => data.length > 0)
            .concat(
                // Add any categories not in our predefined order
                Object.keys(categories)
                    .filter((key) => !categoryOrder.includes(key))
                    .map((categoryKey) => ({
                        key: categoryKey,
                        data: categories[categoryKey] || [],
                    }))
                    .filter(({ data }) => data.length > 0),
            ),
    );

    // Filter categories based on search query and active filters
    const filteredCategories = $derived.by(() => {
        const query = searchQuery.toLowerCase().trim();
        const hasActiveFiltersApplied = hasActiveFilters;

        return sortedCategories
            .map(({ key, data }) => {
                // Filter subcategories based on search query and active filters
                const filteredData = data.filter((subcategory: any) => {
                    // If there are active filters, check if this subcategory has any notes with bean_count > 0
                    if (hasActiveFiltersApplied) {
                        const hasMatchingNotes =
                            subcategory.tasting_notes_with_counts?.some(
                                (noteWithCount: any) =>
                                    noteWithCount.bean_count > 0,
                            );
                        if (!hasMatchingNotes) {
                            return false;
                        }
                    }

                    // If there's a search query, apply search filtering
                    if (query) {
                        // Check if primary category matches
                        const primaryMatches = key
                            .toLowerCase()
                            .includes(query);

                        // Check if secondary category matches
                        const secondaryMatches = subcategory.secondary_category
                            ?.toLowerCase()
                            .includes(query);

                        // Check if any tasting notes match
                        const notesMatch = subcategory.tasting_notes?.some(
                            (note: string) =>
                                note.toLowerCase().includes(query),
                        );

                        return primaryMatches || secondaryMatches || notesMatch;
                    }

                    // If no search query and no active filters, include all
                    return true;
                });

                return {
                    key,
                    data: filteredData,
                };
            })
            .filter(({ data }) => data.length > 0);
    });

    // Calculate global maximum bean count across all tasting notes
    const globalMaxBeanCount = $derived.by(() => {
        const allBeanCounts = sortedCategories
            .flatMap(({ data }) => data)
            .flatMap((sub) => sub.tasting_notes_with_counts || [])
            .map((note) => note.bean_count);

        return allBeanCounts.length > 0 ? Math.max(...allBeanCounts) : 1;
    });

    // Transform data for sunburst chart
    const sunburstData = $derived.by(() => {
        return transformToSunburstData(categories);
    });

    // Function to parse tasting notes query into individual notes
    const activeTastingNotes = $derived.by(() => {
        if (!tastingNotesQuery) return [];

        // Split by & (AND) and | (OR) operators to get individual notes
        // This is a simple parser - for more complex queries, we'd need a proper parser
        const notes = tastingNotesQuery
            .split(/[&|]/)
            .map((note) => note.trim())
            .filter(
                (note) =>
                    note && note !== "General" && note !== "Tasting Notes",
            );

        // Remove duplicates
        return [...new Set(notes)];
    });

    // Function to handle tasting note selection from sunburst chart
    async function handleTastingNoteClick(tastingNote: string) {
        if (!tastingNote) return;

        // Clean the tasting note (remove any "Other" text and trim)
        const cleanedNote = tastingNote.replace(/Other/g, "").trim();
        if (
            !cleanedNote ||
            cleanedNote === "General" ||
            cleanedNote === "Tasting Notes"
        ) {
            return;
        }

        // Check if the note is already in the query
        if (activeTastingNotes.includes(cleanedNote)) {
            return; // Don't add duplicates
        }

        // Add to tasting notes query
        if (tastingNotesQuery) {
            // If there's already a query, append with AND operator
            tastingNotesQuery = `${tastingNotesQuery}&"${cleanedNote}"`;
        } else {
            // If no existing query, just set it
            tastingNotesQuery = `"${cleanedNote}"`;
        }

        // Trigger search with the new tasting note
        await performAdvancedSearch();
    }

    // Function to remove a specific tasting note from the query
    function removeTastingNote(noteToRemove: string) {
        if (!tastingNotesQuery || !noteToRemove) return;

        // Split the query and filter out the note to remove
        const parts = tastingNotesQuery
            .split(/([&|])/)
            .filter((part) => part.trim() !== "");
        const filteredParts: string[] = [];

        for (let i = 0; i < parts.length; i++) {
            const part = parts[i].trim();

            // Skip the note we want to remove
            if (part === noteToRemove) {
                // Also skip the following operator if it exists
                if (i + 1 < parts.length && /[&|]/.test(parts[i + 1])) {
                    i++; // Skip the operator
                }
                continue;
            }

            // Skip leading operators
            if (/[&|]/.test(part) && filteredParts.length === 0) {
                continue;
            }

            filteredParts.push(part);
        }

        // Clean up any trailing operators
        while (
            filteredParts.length > 0 &&
            /[&|]/.test(filteredParts[filteredParts.length - 1])
        ) {
            filteredParts.pop();
        }

        // Update the query
        tastingNotesQuery = filteredParts.join("");

        // Trigger search with the updated query
        performAdvancedSearch();
    }

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
                        newNode.value = d3.sum(
                            filteredChildren,
                            (d) => d.value || 0,
                        );
                    }
                    return newNode;
                }
            }

            return null;
        }

        const filtered = filter(sunburstData);

        // If the root is filtered out, return a default structure
        return filtered || { name: "Tasting Notes", children: [] };
    });
</script>

<svelte:head>
    <title>Coffee Tasting Notes - Kissaten</title>
    <meta
        name="description"
        content="Explore the diverse flavor profiles found in specialty coffee. From fruity and floral to nutty and chocolatey notes."
    />
</svelte:head>

<div class="top-0 left-0 z-0 fixed w-full h-full">
    {#if $flavourImagesEnabled && $flavourImageUrl}
        <!-- {#key $flavourImageDimensions.width + $flavourImageUrl } -->
        {#key $flavourImageUrl}
            <!-- <Scene imageUrl={$flavourImageUrl} /> -->
            <div class="relative w-full h-full">
                <img
                    src={$flavourImageUrl}
                    alt="A painting describing the flavour note"
                    class="w-full h-full object-cover"
                />
                {#if $flavourImageAttribution && ($flavourImageAttribution.image_author || $flavourImageAttribution.image_license)}
                    <div class="right-4 bottom-4 absolute bg-black/70 backdrop-blur-sm px-2 py-1 rounded text-white text-xs">
                        {#if $flavourImageAttribution.image_author}
                            <div class="font-medium">{@html $flavourImageAttribution.image_author}</div>
                        {/if}
                        {#if $flavourImageAttribution.image_license}
                            <div class="text-gray-300">
                                {#if $flavourImageAttribution.image_license_url}
                                    <a href={$flavourImageAttribution.image_license_url} target="_blank" rel="noopener noreferrer" class="hover:text-white underline">
                                        {$flavourImageAttribution.image_license}
                                    </a>
                                {:else}
                                    {$flavourImageAttribution.image_license}
                                {/if}
                            </div>
                        {/if}
                    </div>
                {/if}
            </div>
        {/key}
        <!-- {/key} -->
    {/if}
</div>

<div class="z-10 relative mx-auto px-4 py-8 container">
    <!-- Header -->
    <div class="mb-12 text-center">
        <h1
            class="varietal-title-shadow mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl"
        >
            Coffee Tasting Notes
        </h1>
        <p
            class="varietal-description-shadow mx-auto mb-6 max-w-3xl text-gray-600 dark:text-cyan-300/80 text-xl"
        >
            Explore the diverse flavor profiles found in specialty coffee. Each
            note has been categorized to help you discover patterns and
            understand the complexity of coffee flavors.
        </p>
        <h2
            class="process-category-title-shadow mb-6 font-bold text-gray-900 text-2xl text-center process-category-title-dark"
        >
            Understanding Tasting Notes
        </h2>
        <div
            class="gap-6 grid md:grid-cols-2 lg:grid-cols-3 text-gray-700 text-sm"
        >
            <div
                class="bg-white {$flavourImageUrl
                    ? 'supports-[backdrop-filter]:bg-background/60'
                    : ''} process-card-shadow p-6 rounded-lg process-card-dark"
            >
                <h3
                    class="process-info-title-shadow mb-3 font-semibold text-gray-900 process-category-title-dark"
                >
                    🎯 Origin Impact
                </h3>
                <p class="process-page-description-dark">
                    The soil, climate, and altitude where coffee grows
                    dramatically influences its flavor. Ethiopian coffees often
                    show floral notes, while Brazilian beans may have nutty
                    characteristics.
                </p>
            </div>
            <div
                class="bg-white {$flavourImageUrl
                    ? 'supports-[backdrop-filter]:bg-background/60'
                    : ''} process-card-shadow p-6 rounded-lg process-card-dark"
            >
                <h3
                    class="process-info-title-shadow mb-3 font-semibold text-gray-900 process-category-title-dark"
                >
                    🔥 Processing Methods
                </h3>
                <p class="process-page-description-dark">
                    How the coffee cherry is processed affects flavor
                    development. Natural processing often creates fruity notes,
                    while washed processing highlights acidity and clarity.
                </p>
            </div>
            <div
                class="bg-white {$flavourImageUrl
                    ? 'supports-[backdrop-filter]:bg-background/60'
                    : ''} process-card-shadow p-6 rounded-lg process-card-dark"
            >
                <h3
                    class="process-info-title-shadow mb-3 font-semibold text-gray-900 process-category-title-dark"
                >
                    ⏰ Roast Development
                </h3>
                <p class="process-page-description-dark">
                    Roasting time and temperature create different flavor
                    compounds. Light roasts preserve origin characteristics,
                    while darker roasts develop caramelized and roasted flavors.
                </p>
            </div>
            <div
                class="bg-white {$flavourImageUrl
                    ? 'supports-[backdrop-filter]:bg-background/60'
                    : ''} process-card-shadow p-6 rounded-lg process-card-dark"
            >
                <h3
                    class="process-info-title-shadow mb-3 font-semibold text-gray-900 process-category-title-dark"
                >
                    🌱 Variety Influence
                </h3>
                <p class="process-page-description-dark">
                    Different coffee varieties have distinct flavor potentials.
                    Geisha varieties often show floral and tea-like qualities,
                    while Bourbon varieties may be sweet and balanced.
                </p>
            </div>
            <div
                class="bg-white {$flavourImageUrl
                    ? 'supports-[backdrop-filter]:bg-background/60'
                    : ''} process-card-shadow p-6 rounded-lg process-card-dark"
            >
                <h3
                    class="process-info-title-shadow mb-3 font-semibold text-gray-900 process-category-title-dark"
                >
                    👨‍🍳 Brewing Impact
                </h3>
                <p class="process-page-description-dark">
                    Your brewing method affects which flavors are extracted.
                    Pour-over methods highlight acidity and brightness, while
                    espresso emphasizes body and sweetness.
                </p>
            </div>
        </div>
    </div>

    <!-- Main Content Area with Sidebar Layout -->
    <div class="flex lg:flex-row flex-col gap-2 lg:gap-8">
        <!-- Advanced Filters Sidebar -->
        {#if showAdvancedFilters}
            <div class="w-full lg:w-fit">
                <div
                    class="bg-white {$flavourImageUrl
                        ? 'supports-[backdrop-filter]:bg-background/60'
                        : ''} dark:bg-slate-800/60 shadow-lg p-6 border border-gray-200 dark:border-cyan-500/30 rounded-xl"
                >
                    <div class="flex justify-between items-center mb-4">
                        <h3
                            class="font-semibold text-gray-900 dark:text-cyan-100 text-lg"
                        >
                            Filter tasting notes by...
                        </h3>
                        <button
                            onclick={() => (showAdvancedFilters = false)}
                            class="text-gray-400 hover:text-gray-600 dark:hover:text-cyan-300 dark:text-cyan-400/70"
                            aria-label="Close advanced filters"
                        >
                            <svg
                                class="w-5 h-5"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                    stroke-width="2"
                                    d="M6 18L18 6M6 6l12 12"
                                />
                            </svg>
                        </button>
                    </div>

                    <SearchFilters
                        bind:searchQuery={advancedSearchQuery}
                        bind:tastingNotesQuery
                        bind:roasterFilter
                        bind:roasterLocationFilter
                        bind:originFilter
                        bind:roastLevelFilter
                        bind:roastProfileFilter
                        bind:processFilter
                        bind:varietyFilter
                        bind:minPrice
                        bind:maxPrice
                        bind:minWeight
                        bind:maxWeight
                        bind:minElevation
                        bind:maxElevation
                        bind:regionFilter
                        bind:producerFilter
                        bind:farmFilter
                        bind:inStockOnly
                        bind:isDecaf
                        bind:isSingleOrigin
                        bind:sortBy
                        bind:sortOrder
                        bind:showFilters={showAdvancedFilters}
                        originOptions={data.originOptions}
                        allRoasters={data.allRoasters}
                        roasterLocationOptions={data.roasterLocationOptions}
                        onSearch={performAdvancedSearch}
                        onClearFilters={clearAdvancedFilters}
                    />
                    <!-- Link to search page with current filters -->
                    {#if hasActiveFilters}
                        <div class="mt-4">
                            <Button
                                class="w-full"
                                onclick={() =>
                                    (window.location.href = searchPageUrl)}
                            >
                                <Coffee class="mr-2 w-4 h-4" />
                                {#await totalBeanCount}
                                    View beans
                                {:then count}
                                    View {count.toLocaleString()} bean{count ===
                                    1
                                        ? ""
                                        : "s"}
                                {/await}
                            </Button>
                        </div>
                    {/if}
                </div>
            </div>
        {/if}

        <!-- Main Content -->
        <div class="flex-1">
            <!-- Search Bar and Advanced Filters -->
            <div class="mx-auto mb-8 max-w-xl">
                <div class="flex items-center gap-2">
                    <!-- Original Search Bar -->
                    <div class="relative flex-1 grow">
                        <Search
                            class="top-1/2 left-3 absolute w-4 h-4 text-gray-500 dark:text-cyan-400/70 -translate-y-1/2 transform"
                        />
                        <Input
                            bind:value={searchQuery}
                            placeholder="Search tasting notes, categories..."
                            class="bg-white dark:bg-slate-700/60 pl-10 border-gray-200 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 focus:ring-orange-500 dark:focus:ring-emerald-500/50 text-gray-900 dark:placeholder:text-cyan-400/70 dark:text-cyan-200 placeholder:text-gray-500"
                        />
                    </div>

                    <!-- Advanced Filters Toggle Button -->
                    <Button
                        variant="outline"
                        size="icon"
                        onclick={() =>
                            (showAdvancedFilters = !showAdvancedFilters)}
                        class="relative {showAdvancedFilters
                            ? 'ring-2 ring-orange-500 dark:ring-emerald-500/50'
                            : ''} {hasActiveFilters
                            ? 'border-orange-500 dark:border-emerald-500'
                            : ''}"
                        title="Toggle advanced filters panel to limit to specific beans"
                        aria-label="Toggle advanced filters"
                    >
                        <Filter
                            class="w-4 h-4 {hasActiveFilters
                                ? 'text-orange-600 dark:text-emerald-400'
                                : ''}"
                        />
                        {#if hasActiveFilters}
                            <div
                                class="top-0 right-0 absolute bg-orange-500 dark:bg-emerald-500 rounded-full w-2 h-2 -translate-y-1 translate-x-1 transform"
                            ></div>
                        {/if}
                    </Button>
                    <!-- Link to search page with current filters -->
                    {#if hasActiveFilters}
                        <Button
                            onclick={() =>
                                (window.location.href = searchPageUrl)}
                        >
                            <Coffee class="mr-2 w-4 h-4" />
                            {#await totalBeanCount}
                                View
                            {:then count}
                                {#if count > 0}
                                    View {count.toLocaleString()} bean{count ===
                                    1
                                        ? ""
                                        : "s"}
                                {:else}
                                    View
                                {/if}
                            {/await}
                        </Button>
                    {/if}
                </div>

                {#if isLoading}
                    <div
                        class="flex justify-center items-center mt-4 text-gray-500 dark:text-cyan-400/80"
                    >
                        <div class="flex items-center gap-2">
                            <div
                                class="border-2 border-gray-300 dark:border-cyan-400/30 border-t-gray-600 dark:border-t-cyan-400 rounded-full w-4 h-4 animate-spin"
                            ></div>
                            <span class="text-sm"
                                >Filtering beans...</span
                            >
                        </div>
                    </div>
                {:else if searchQuery && categories && Object.keys(categories).length === 0}
                    <p
                        class="mt-4 text-gray-500 dark:text-cyan-400/80 text-center"
                    >
                        No tasting notes found matching "{searchQuery}". Try a
                        different search term.
                    </p>
                {/if}

                <!-- Active Tasting Notes Display (shared between both views) -->
                {#if activeTastingNotes.length > 0}
                    <div
                        class="bg-orange-50 dark:bg-emerald-900/20 mt-2 p-1 border border-orange-200 dark:border-emerald-700/40 rounded-lg"
                    >
                        <div class="flex flex-wrap gap-2">
                            {#each activeTastingNotes as note}
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onclick={() => removeTastingNote(note)}
                                    class="flex items-center gap-2 touch-manipulation"
                                    title="Click to remove {note} from search"
                                    aria-label="Remove {note} from search"
                                >
                                    <span class="text-sm">{note}</span>
                                    <svg
                                        class="flex-shrink-0 w-4 h-4"
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                    >
                                        <path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            stroke-width="2"
                                            d="M6 18L18 6M6 6l12 12"
                                        />
                                    </svg>
                                </Button>
                            {/each}
                        </div>
                    </div>
                {/if}
            </div>
            <!-- View Toggle -->
            <div class="justify-center grid grid-cols-1 lg:grid-cols-3 mb-2">
                <div class="hidden lg:block"></div>
                <div
                    class="justify-center justify-self-center items-center grid grid-cols-2 bg-gray-100 dark:bg-slate-700/60 p-1 border border-gray-200 dark:border-slate-600 rounded-lg w-fit"
                >
                    <button
                        onclick={() => (showSunburst = false)}
                        class="px-4 py-2 text-sm flex flex-col justify-center items-center gap-2 font-medium rounded-md transition-colors {showSunburst
                            ? 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-cyan-100'
                            : 'bg-white dark:bg-slate-600 text-gray-900 dark:text-cyan-100 shadow-sm hover:bg-gray-100 dark:hover:bg-slate-500/60'}"
                    >
                        <List class="w-6 h-6" /> List
                    </button>
                    <button
                        onclick={() => (showSunburst = true)}
                        class="px-4 py-2 text-sm flex flex-col justify-center items-center gap-2 font-medium rounded-md transition-colors {showSunburst
                            ? 'bg-white dark:bg-slate-600 text-gray-900 dark:text-cyan-100 shadow-sm hover:bg-gray-100 dark:hover:bg-slate-500/60'
                            : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-cyan-100'}"
                    >
                        <Target class="w-6 h-6" /> Sunburst
                    </button>
                </div>

        <!-- Images Toggle -->
        <div class="hidden lg:flex justify-center justify-self-end items-end space-x-2">
                <Switch id="flavour-images"
                    bind:checked={$flavourImagesEnabled}
                />
                <Label for="flavour-images">Images {$flavourImagesEnabled ? "enabled" : "disabled"}</Label>
        </div>
            </div>

            {#if !showSunburst}
                <!-- Tasting Note Categories Grid -->
                <div class="space-y-6">
                    {#each filteredCategories as { key, data }}
                        <!-- Group subcategories by secondary_category -->
                        {@const grouped = (() => {
                            const map = new Map();
                            for (const sub of data) {
                                const sec = sub.secondary_category || "General";
                                if (!map.has(sec)) map.set(sec, []);
                                map.get(sec).push(sub);
                            }
                            return Array.from(map.entries());
                        })()}
                        <div
                            id={`category-${key.replace(/[^a-zA-Z0-9]/g, "-")}`}
                            class="bg-white {$flavourImageUrl
                                ? 'supports-[backdrop-filter]:bg-background/60'
                                : ''} dark:bg-slate-800/60 shadow-sm hover:shadow-md dark:hover:shadow-cyan-500/20 dark:shadow-cyan-500/10 pr-2 pb-2 md:p-6 border border-gray-200 dark:border-cyan-500/30 rounded-xl transition-shadow scroll-mt-24"
                        >
                            <h2
                                class="flex items-center gap-2 my-2 font-semibold text-gray-900 dark:text-cyan-100 text-2xl"
                            >
                                <a
                                    href={`#category-${key.replace(/[^a-zA-Z0-9]/g, "-")}`}
                                    class="px-1 rounded focus:outline-none focus:ring-2 focus:ring-orange-400 decoration-dotted hover:underline"
                                    title="Link to {key}"
                                >
                                    {getCategoryEmoji(key)}
                                    {key}
                                </a>
                            </h2>
                            <div class="space-y-4 ml-2">
                                {#each grouped as [secondary, subs]}
                                    <TastingNoteCategoryCard
                                        primaryCategory={key}
                                        secondaryCategory={secondary}
                                        subcategories={subs}
                                        {searchQuery}
                                        {globalMaxBeanCount}
                                        onTastingNoteClick={handleTastingNoteClick}
                                    />
                                {/each}
                            </div>
                        </div>
                    {/each}

                    {#if filteredCategories.length === 0 && !searchQuery}
                        <div class="py-12 text-center">
                            <p
                                class="text-gray-500 dark:text-cyan-400/80 text-lg"
                            >
                                No tasting note categories available.
                            </p>
                        </div>
                    {/if}
                </div>
            {:else}
                <!-- Sunburst Chart Section -->
                <div
                    class="sticky top-16 bg-white {$flavourImageUrl
                        ? 'supports-[backdrop-filter]:bg-background/60'
                        : ''} dark:bg-slate-800/60 shadow-lg mx-auto p-4 border border-gray-200 dark:border-cyan-500/30 rounded-xl max-w-8xl z-10"
                >
                    <div
                        class="mb-4 text-gray-500 dark:text-cyan-400/70 text-sm text-center"
                    >
                        <p>
                            Hover over segments to see details. Click categories
                            to zoom in, or click tasting notes to add them to
                            your search filters.
                        </p>
                    </div>

                    <div class="w-full max-h-[70vh] aspect-square">
                        {#if filteredSunburstData.children && filteredSunburstData.children.length > 0}
                            <SunburstChart
                                data={filteredSunburstData}
                                className="w-full h-full"
                                onTastingNoteClick={handleTastingNoteClick}
                            />
                        {:else}
                            <div
                                class="flex justify-center items-center w-full h-full text-gray-500 dark:text-cyan-400/80"
                            >
                                <div class="text-center">
                                    <div class="mb-4 text-4xl">📊</div>
                                    <p class="text-lg">
                                        No tasting note data available
                                    </p>
                                    <p class="text-sm">
                                        Try refreshing the page or check back
                                        later
                                    </p>
                                </div>
                            </div>
                        {/if}
                    </div>
                </div>
            {/if}
        </div>
    </div>
</div>
