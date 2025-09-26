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

        // Data is now already grouped by primary category with metadata
        const { categories, metadata } = result.data;

        // Sort subcategories within each primary category by note count
        for (const primaryKey in categories) {
            categories[primaryKey].sort((a: any, b: any) => (b.note_count || 0) - (a.note_count || 0));
        }

        return {
            categories,
            metadata
        };
    } catch (err) {
        console.error('Error loading tasting note categories:', err);
        throw error(500, 'Failed to load tasting note categories');
    }
};