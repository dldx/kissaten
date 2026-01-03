<script lang="ts">
    import { getFlavourCategoryColors } from "$lib/utils";
    import { fetchAndSetFlavourImage, clearFlavourImage } from '$lib/services/flavourImageService';
    import { onMount } from "svelte";

    interface TastingNoteSubcategory {
        primary_category: string;
        secondary_category: string | null;
        tertiary_category: string | null;
        note_count: number;
        bean_count: number;
        tasting_notes: string[];
        tasting_notes_with_counts: Array<{ note: string; bean_count: number }>;
    }

    interface Props {
        primaryCategory: string;
        secondaryCategory?: string;
        subcategories: TastingNoteSubcategory[];
        searchQuery?: string;
        globalMaxBeanCount: number;
        onTastingNoteClick?: (tastingNote: string) => void;
    }

    let { primaryCategory, secondaryCategory, subcategories, searchQuery = "", onTastingNoteClick }: Props = $props();

    let isVisible = $state(false);
    let categoryElement: HTMLDivElement;

    onMount(() => {
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        isVisible = true;
                        // Once visible, we don't need to observe anymore
                        observer.disconnect();
                    }
                });
            },
            {
                rootMargin: "100px", // Start loading slightly before element comes into view
                threshold: 0,
            }
        );

        if (categoryElement) {
            observer.observe(categoryElement);
        }

        return () => {
            observer.disconnect();
        };
    });


    const categoryColors = $derived(getFlavourCategoryColors(primaryCategory));

    // Filter individual tasting notes based on search query
    const getFilteredTastingNotes = (notes: string[]) => {
        if (!searchQuery.trim()) {
            return [...notes].sort();
        }

        const query = searchQuery.toLowerCase().trim();
        return notes
            .filter((note) => note.toLowerCase().includes(query))
            .sort();
    };

    // Get tasting notes with bean counts for scaling
    const getTastingNotesWithCounts = (subcategory: TastingNoteSubcategory) => {
        const filteredNotes = getFilteredTastingNotes(
            subcategory.tasting_notes || [],
        );

        // Use actual counts from API
        return subcategory.tasting_notes_with_counts
            .filter((item) => filteredNotes.includes(item.note))
            .filter((item) => item.bean_count > 0)
            .toSorted((a, b) => b.bean_count - a.bean_count);
    };

    function handleFlavourMouseEnter(notes: string[]) {
        fetchAndSetFlavourImage(notes);
    }

    function handleFlavourMouseLeave() {
        clearFlavourImage();
    }
</script>

<div
    bind:this={categoryElement}
    class="bg-gray-50/50 dark:bg-slate-700/30 backdrop-opacity-10 p-2 md:p-4 border border-gray-100 dark:border-slate-600/50 rounded-lg scroll-mt-24"
>
    <!-- Header -->
    <div
        id={`subcategory-${(primaryCategory + '-' + (secondaryCategory || "General")).replace(/[^a-zA-Z0-9]/g, "-")}`}
        class="scroll-mt-24"
    >
        <h2 class="font-semibold text-gray-900 dark:text-cyan-100 text-xl">
            <a
                href={`#subcategory-${(primaryCategory + '-' + (secondaryCategory || "General")).replace(/[^a-zA-Z0-9]/g, "-")}`}
                class="rounded focus:outline-none focus:ring-2 focus:ring-orange-400 decoration-dotted hover:underline"
                title={`Link to ${secondaryCategory}`}
            >
                {secondaryCategory}
            </a>
        </h2>
    </div>

    <!-- Subcategories with their tasting notes -->
    {#if isVisible}
        {#if subcategories.length > 0}
            <div class="space-y-4 mt-2 mb-2 md:mb-6">
                <!-- Move null tertiary category to end of list -->
                {#each [...subcategories].sort((a, b) => (a.tertiary_category ? 0 : 1) - (b.tertiary_category ? 0 : 1)) as subcategory}
                <div
                    class="pl-4 border-gray-200 dark:border-slate-600/50 border-l-2"
                >
                    <div class="flex justify-between items-center mb-3">
                        <h3
                            class="font-medium text-gray-900 text-md dark:text-cyan-200 text-base"
                        >
                            {subcategory.tertiary_category || (subcategories.length === 1 ? "" : "Other Notes")}
                        </h3>
                    </div>

                    {#if subcategory.tasting_notes && subcategory.tasting_notes.length > 0}
                        {@const notesWithCounts =
                            getTastingNotesWithCounts(subcategory)}
                        {#if notesWithCounts.length > 0}
                            <div class="flex flex-wrap gap-0 mb-2">
                                {#each notesWithCounts as { note, bean_count }}
                                    {#if onTastingNoteClick}
                                        <button
                                            class={`m-0.5 inline-block ${categoryColors.bg} ${categoryColors.darkBg} hover:bg-gray-200 dark:hover:bg-slate-600/50 px-2 py-1 rounded text-gray-700 ${categoryColors.darkText} text-sm transition-colors cursor-pointer`}
                                            onclick={() => onTastingNoteClick?.(note)}
                                            onmouseenter={() => handleFlavourMouseEnter([note, subcategory.secondary_category ? subcategory.secondary_category : subcategory.primary_category, subcategory.primary_category])}
                                            onmouseleave={handleFlavourMouseLeave}
                                        >
                                            <span class="block leading-tight"
                                                >{note} ({bean_count})</span
                                            >
                                        </button>
                                    {:else}
                                        <a
                                            class={`m-0.5 inline-block ${categoryColors.bg} ${categoryColors.darkBg} hover:bg-gray-200 dark:hover:bg-slate-600/50 px-2 py-1 rounded text-gray-700 ${categoryColors.darkText} text-sm transition-colors `}
                                            href={`/search?tasting_notes_query="${encodeURIComponent(note)}"`}
                                            onmouseenter={() => handleFlavourMouseEnter([note, subcategory.secondary_category ? subcategory.secondary_category : subcategory.primary_category, subcategory.primary_category])}
                                            onmouseleave={handleFlavourMouseLeave}
                                        >
                                            <span class="block leading-tight"
                                                >{note} ({bean_count})</span
                                            >
                                        </a>
                                    {/if}
                                {/each}
                            </div>
                        {:else if searchQuery.trim()}
                            <p
                                class="text-gray-500 dark:text-cyan-400/70 text-sm italic"
                            >
                                No notes match "{searchQuery}" in this
                                subcategory
                            </p>
                        {:else}
                            <p
                                class="text-gray-500 dark:text-cyan-400/70 text-sm italic"
                            >
                                No specific notes available
                            </p>
                        {/if}
                    {:else}
                        <p
                            class="text-gray-500 dark:text-cyan-400/70 text-sm italic"
                        >
                            No specific notes available
                        </p>
                    {/if}
                </div>
            {/each}
        </div>
        {/if}
    {:else}
        <!-- Placeholder to maintain layout before loading -->
        <div class="h-32 flex items-center justify-center text-gray-400 mt-2">
            <div class="animate-pulse">Loading tasting notes...</div>
        </div>
    {/if}
</div>
