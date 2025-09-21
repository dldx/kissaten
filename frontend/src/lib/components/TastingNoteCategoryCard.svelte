<script lang="ts">
    interface TastingNoteSubcategory {
        primary_category: string;
        secondary_category: string | null;
        tertiary_category: string | null;
        note_count: number;
        bean_count: number;
        tasting_notes: string[];
        tasting_notes_with_counts: Array<{note: string, bean_count: number}>;
    }

    interface Props {
        primaryCategory: string;
        subcategories: TastingNoteSubcategory[];
        searchQuery?: string;
        globalMaxBeanCount: number;
    }

    let { primaryCategory, subcategories, searchQuery = '' }: Props = $props();

    // Get category emoji
    const getCategoryEmoji = (category: string) => {
        const emojiMap: Record<string, string> = {
            'Fruity': '🍓',
            'Cocoa': '🍫',
            'Nutty': '🥜',
            'Floral': '🌸',
            'Sweet': '🍯',
            'Spicy': '🌶️',
            'Earthy': '🌱',
            'Roasted': '🔥',
            'Green/Vegetative': '🥬',
            'Sour/Fermented': '🍋',
            'Alcohol/Fermented': '🍷',
            'Chemical': '⚗️',
            'Papery/Musty': '📰',
            'Other': '☕'
        };
        return emojiMap[category] || '☕';
    };

    // Get category color scheme
    const getCategoryColors = (category: string) => {
        const colorMap: Record<string, { bg: string; text: string; border: string; darkBg: string; darkText: string; darkBorder: string }> = {
            'Fruity': { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-200', darkBg: 'dark:bg-red-900/30', darkText: 'dark:text-red-300', darkBorder: 'dark:border-red-700/50' },
            'Cocoa': { bg: 'bg-amber-100', text: 'text-amber-800', border: 'border-amber-200', darkBg: 'dark:bg-amber-900/30', darkText: 'dark:text-amber-300', darkBorder: 'dark:border-amber-700/50' },
            'Nutty': { bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-200', darkBg: 'dark:bg-yellow-900/30', darkText: 'dark:text-yellow-300', darkBorder: 'dark:border-yellow-700/50' },
            'Floral': { bg: 'bg-pink-100', text: 'text-pink-800', border: 'border-pink-200', darkBg: 'dark:bg-pink-900/30', darkText: 'dark:text-pink-300', darkBorder: 'dark:border-pink-700/50' },
            'Sweet': { bg: 'bg-purple-100', text: 'text-purple-800', border: 'border-purple-200', darkBg: 'dark:bg-purple-900/30', darkText: 'dark:text-purple-300', darkBorder: 'dark:border-purple-700/50' },
            'Spicy': { bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-200', darkBg: 'dark:bg-orange-900/30', darkText: 'dark:text-orange-300', darkBorder: 'dark:border-orange-700/50' },
            'Earthy': { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-200', darkBg: 'dark:bg-green-900/30', darkText: 'dark:text-green-300', darkBorder: 'dark:border-green-700/50' },
            'Roasted': { bg: 'bg-stone-100', text: 'text-stone-800', border: 'border-stone-200', darkBg: 'dark:bg-stone-900/30', darkText: 'dark:text-stone-300', darkBorder: 'dark:border-stone-700/50' },
            'Green/Vegetative': { bg: 'bg-lime-100', text: 'text-lime-800', border: 'border-lime-200', darkBg: 'dark:bg-lime-900/30', darkText: 'dark:text-lime-300', darkBorder: 'dark:border-lime-700/50' },
            'Sour/Fermented': { bg: 'bg-cyan-100', text: 'text-cyan-800', border: 'border-cyan-200', darkBg: 'dark:bg-cyan-900/30', darkText: 'dark:text-cyan-300', darkBorder: 'dark:border-cyan-700/50' },
            'Alcohol/Fermented': { bg: 'bg-indigo-100', text: 'text-indigo-800', border: 'border-indigo-200', darkBg: 'dark:bg-indigo-900/30', darkText: 'dark:text-indigo-300', darkBorder: 'dark:border-indigo-700/50' },
            'Chemical': { bg: 'bg-slate-100', text: 'text-slate-800', border: 'border-slate-200', darkBg: 'dark:bg-slate-900/30', darkText: 'dark:text-slate-300', darkBorder: 'dark:border-slate-700/50' },
            'Papery/Musty': { bg: 'bg-neutral-100', text: 'text-neutral-800', border: 'border-neutral-200', darkBg: 'dark:bg-neutral-900/30', darkText: 'dark:text-neutral-300', darkBorder: 'dark:border-neutral-700/50' },
            'Other': { bg: 'bg-gray-100', text: 'text-gray-800', border: 'border-gray-200', darkBg: 'dark:bg-gray-900/30', darkText: 'dark:text-gray-300', darkBorder: 'dark:border-gray-700/50' }
        };
        return colorMap[category] || { bg: 'bg-gray-100', text: 'text-gray-800', border: 'border-gray-200', darkBg: 'dark:bg-gray-900/30', darkText: 'dark:text-gray-300', darkBorder: 'dark:border-gray-700/50' };
    };

    const categoryColors = $derived(getCategoryColors(primaryCategory));

    // Filter individual tasting notes based on search query
    const getFilteredTastingNotes = (notes: string[]) => {
        if (!searchQuery.trim()) {
            return notes.sort();
        }

        const query = searchQuery.toLowerCase().trim();
        return notes
            .filter(note => note.toLowerCase().includes(query))
            .sort();
    };

    // Get tasting notes with bean counts for scaling
    const getTastingNotesWithCounts = (subcategory: TastingNoteSubcategory) => {
        const filteredNotes = getFilteredTastingNotes(subcategory.tasting_notes || []);

        // Use actual counts from API
        return subcategory.tasting_notes_with_counts
            .filter(item => filteredNotes.includes(item.note))
            .sort((a, b) => b.bean_count - a.bean_count);
    };

</script>

<div class="bg-white dark:bg-slate-800/60 shadow-sm hover:shadow-md dark:hover:shadow-cyan-500/20 dark:shadow-cyan-500/10 p-6 border border-gray-200 dark:border-cyan-500/30 rounded-xl transition-shadow">
    <!-- Header -->
    <div class="flex justify-between items-center mb-4">
        <div class="flex items-center space-x-3">
            <span class="text-2xl">{getCategoryEmoji(primaryCategory)}</span>
            <div>
                <h2 class="font-semibold text-gray-900 dark:text-cyan-100 text-xl">
                    {primaryCategory}
                </h2>
            </div>
        </div>
    </div>

    <!-- Subcategories with their tasting notes -->
    {#if subcategories.length > 0}
        <div class="space-y-4 mb-6">
            {#each subcategories as subcategory}
                <div class="bg-gray-50/50 dark:bg-slate-700/30 p-4 border border-gray-100 dark:border-slate-600/50 rounded-lg">
                    <div class="flex justify-between items-center mb-3">
                        <h3 class="font-medium text-gray-900 dark:text-cyan-200 text-base">
                            {subcategory.secondary_category || 'General'}{#if subcategory.tertiary_category}&nbsp;-&nbsp;{subcategory.tertiary_category}{/if}
                        </h3>
                    </div>

                    {#if subcategory.tasting_notes && subcategory.tasting_notes.length > 0}
                        {@const notesWithCounts = getTastingNotesWithCounts(subcategory)}
                        {#if notesWithCounts.length > 0}
		<div class="flex flex-wrap gap-1 mb-2">
                                {#each notesWithCounts as { note, bean_count }}
                                    <a
                                    class={`inline-block ${categoryColors.bg} ${categoryColors.darkBg} hover:bg-gray-200 dark:hover:bg-slate-600/50 px-2 py-1 rounded text-gray-700 ${categoryColors.darkText} text-sm transition-colors`}
                                        href={`/search?tasting_notes_query="${encodeURIComponent(note)}"`}
                                    >
                                        <span class="block leading-tight">{note} ({bean_count})</span>
                                    </a>
                                {/each}
                        </div>
                        {:else if searchQuery.trim()}
                            <p class="text-gray-500 dark:text-cyan-400/70 text-sm italic">No notes match "{searchQuery}" in this subcategory</p>
                        {:else}
                            <p class="text-gray-500 dark:text-cyan-400/70 text-sm italic">No specific notes available</p>
                        {/if}
                    {:else}
                        <p class="text-gray-500 dark:text-cyan-400/70 text-sm italic">No specific notes available</p>
                    {/if}
                </div>
            {/each}
        </div>
    {/if}

</div>