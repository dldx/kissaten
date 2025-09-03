import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageLoad = async ({ fetch }) => {
    try {
        const response = await fetch('/api/v1/tasting-note-categories');

        if (!response.ok) {
            throw error(response.status, 'Failed to load tasting note categories');
        }

        const result = await response.json();

        if (!result.success) {
            throw error(500, result.message || 'Failed to load tasting note categories');
        }

        // Group categories by primary category
        const groupedCategories: Record<string, any[]> = {};
        let totalNotes = 0;
        let totalBeans = 0;
        let totalUniqueDescriptors = 0;

        for (const category of result.data) {
            const primaryKey = category.primary_category || 'Other';

            if (!groupedCategories[primaryKey]) {
                groupedCategories[primaryKey] = [];
            }

            groupedCategories[primaryKey].push(category);
            totalNotes += category.note_count || 0;
            totalBeans += category.bean_count || 0;
            totalUniqueDescriptors += (category.tasting_notes || []).length;
        }

        // Sort subcategories within each primary category by note count
        for (const primaryKey in groupedCategories) {
            groupedCategories[primaryKey].sort((a, b) => (b.note_count || 0) - (a.note_count || 0));
        }

        return {
            categories: groupedCategories,
            metadata: {
                total_notes: totalNotes,
                total_beans: totalBeans,
                total_primary_categories: Object.keys(groupedCategories).length,
                total_unique_descriptors: totalUniqueDescriptors
            }
        };
    } catch (err) {
        console.error('Error loading tasting note categories:', err);
        throw error(500, 'Failed to load tasting note categories');
    }
};