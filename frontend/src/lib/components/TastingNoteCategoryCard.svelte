<script lang="ts">
    import { getFlavourCategoryColors } from "$lib/utils";

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
    }

    let { primaryCategory, secondaryCategory, subcategories, searchQuery = "" }: Props = $props();


    const categoryColors = $derived(getFlavourCategoryColors(primaryCategory));

    // Filter individual tasting notes based on search query
    const getFilteredTastingNotes = (notes: string[]) => {
        if (!searchQuery.trim()) {
            return notes.sort();
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
            .sort((a, b) => b.bean_count - a.bean_count);
    };
</script>

<div
    class="bg-gray-50/50 dark:bg-slate-700/30 p-4 border border-gray-100 dark:border-slate-600/50 rounded-lg scroll-mt-24"
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
                title={`Link to ${secondaryCategory || "General"}`}
            >
                {secondaryCategory}
            </a>
        </h2>
    </div>

    <!-- Subcategories with their tasting notes -->
    {#if subcategories.length > 0}
        <div class="space-y-4 mt-2 mb-6">
            {#each subcategories as subcategory}
                <div
                    class="pl-4 border-gray-200 dark:border-slate-600/50 border-l-2"
                >
                    <div class="flex justify-between items-center mb-3">
                        <h3
                            class="font-medium text-gray-900 text-md dark:text-cyan-200 text-base"
                        >
                            {#if subcategory.tertiary_category}{subcategory.tertiary_category}{/if}
                        </h3>
                    </div>

                    {#if subcategory.tasting_notes && subcategory.tasting_notes.length > 0}
                        {@const notesWithCounts =
                            getTastingNotesWithCounts(subcategory)}
                        {#if notesWithCounts.length > 0}
                            <div class="flex flex-wrap gap-1 mb-2">
                                {#each notesWithCounts as { note, bean_count }}
                                    <a
                                        class={`inline-block ${categoryColors.bg} ${categoryColors.darkBg} hover:bg-gray-200 dark:hover:bg-slate-600/50 px-2 py-1 rounded text-gray-700 ${categoryColors.darkText} text-sm transition-colors`}
                                        href={`/search?tasting_notes_query="${encodeURIComponent(note)}"`}
                                    >
                                        <span class="block leading-tight"
                                            >{note} ({bean_count})</span
                                        >
                                    </a>
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
</div>
