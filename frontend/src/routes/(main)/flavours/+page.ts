import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';
import { currencyState } from '$lib/stores/currency.svelte';

export const load: PageLoad = async ({ fetch, url, parent }) => {
    try {
        // Get parent data for dropdown options
        const parentData = await parent();

        // Extract search parameters from URL
        const urlParams = url.searchParams;
        const searchQuery = urlParams.get('q') || '';
        const tastingNotesQuery = urlParams.get('tasting_notes_query') || '';
        const roasterFilter = urlParams.getAll('roaster');
        const roasterLocationFilter = urlParams.getAll('roaster_location');
        const originFilter = urlParams.getAll('origin');
        const regionFilter = urlParams.get('region') || '';
        const producerFilter = urlParams.get('producer') || '';
        const farmFilter = urlParams.get('farm') || '';
        const roastLevelFilter = urlParams.get('roast_level') || '';
        const roastProfileFilter = urlParams.get('roast_profile') || '';
        const processFilter = urlParams.get('process') || '';
        const varietyFilter = urlParams.get('variety') || '';
        const minPrice = urlParams.get('min_price') || '';
        const maxPrice = urlParams.get('max_price') || '';
        const minWeight = urlParams.get('min_weight') || '';
        const maxWeight = urlParams.get('max_weight') || '';
        const minElevation = urlParams.get('min_elevation') || '';
        const maxElevation = urlParams.get('max_elevation') || '';
        const minCuppingScore = urlParams.get('min_cupping_score') || '';
        const maxCuppingScore = urlParams.get('max_cupping_score') || '';
        const inStockOnly = urlParams.get('in_stock_only') === 'true';
        const isDecaf = urlParams.get('is_decaf') === 'true' ? true : urlParams.get('is_decaf') === 'false' ? false : undefined;
        const isSingleOrigin = urlParams.get('is_single_origin') === 'true' ? true : urlParams.get('is_single_origin') === 'false' ? false : undefined;

        // Build API URL with parameters
        const apiUrl = new URL('/api/v1/tasting-note-categories', url.origin);

        // Add parameters to API URL if they exist
        if (searchQuery) apiUrl.searchParams.set('query', searchQuery);
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
        if (minCuppingScore) apiUrl.searchParams.set('min_cupping_score', minCuppingScore);
        if (maxCuppingScore) apiUrl.searchParams.set('max_cupping_score', maxCuppingScore);
        if (inStockOnly) apiUrl.searchParams.set('in_stock_only', 'true');
        if (isDecaf !== undefined) apiUrl.searchParams.set('is_decaf', isDecaf.toString());
        if (isSingleOrigin !== undefined) apiUrl.searchParams.set('is_single_origin', isSingleOrigin.toString());
        if (currencyState.selectedCurrency) apiUrl.searchParams.set('convert_to_currency', currencyState.selectedCurrency);

        const response = await fetch(apiUrl.toString());

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
            metadata,
            // Pass through parent data for SearchFilters
            originOptions: parentData.originOptions,
            allRoasters: parentData.allRoasters,
            roasterLocationOptions: parentData.roasterLocationOptions,
            // Pass through filter parameters
            filterParams: {
                searchQuery,
                tastingNotesQuery,
                roasterFilter,
                roasterLocationFilter,
                originFilter,
                regionFilter,
                producerFilter,
                farmFilter,
                roastLevelFilter,
                roastProfileFilter,
                processFilter,
                varietyFilter,
                minPrice,
                maxPrice,
                minWeight,
                maxWeight,
                minElevation,
                maxElevation,
                minCuppingScore,
                maxCuppingScore,
                inStockOnly,
                isDecaf,
                isSingleOrigin
            }
        };
    } catch (err) {
        console.error('Error loading tasting note categories:', err);
        throw error(500, 'Failed to load tasting note categories');
    }
};