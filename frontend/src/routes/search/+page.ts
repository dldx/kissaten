import { api, type CoffeeBean } from '$lib/api.js';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ url, fetch }) => {
	try {
		// Extract search parameters from URL
		const urlParams = url.searchParams;
		const searchQuery = urlParams.get('q') || '';
		const tastingNotesQuery = urlParams.get('tasting_notes_query') || '';
		const smartQuery = urlParams.get('smart_query') || '';
		const roasterFilter = urlParams.getAll('roaster');
		const roasterLocationFilter = urlParams.getAll('roaster_location');
		const countryFilter = urlParams.getAll('country');
		const regionFilter = urlParams.getAll('region') || [];
		const producerFilter = urlParams.getAll('producer') || [];
		const farmFilter = urlParams.getAll('farm') || [];
		const roastLevelFilter = urlParams.get('roast_level') || '';
		const roastProfileFilter = urlParams.get('roast_profile') || '';
		const processFilter = urlParams.getAll('process') || [];
		const varietyFilter = urlParams.getAll('variety') || [];
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
		const tastingNotesOnly = urlParams.get('tasting_notes_only') === 'true';
		const sortBy = urlParams.get('sort_by') || 'scraped_at';
		const sortOrder = urlParams.get('sort_order') || 'desc';
		const currentPage = 1; // Always start from page 1 for infinite scroll
		const perPage = 20;

		// Build search parameters - updated for new schema with origins
		const params = {
			query: searchQuery || undefined,
			tasting_notes_query: tastingNotesQuery || undefined,
			roaster: roasterFilter.length > 0 ? roasterFilter : undefined,
			roaster_location: roasterLocationFilter.length > 0 ? roasterLocationFilter : undefined,
			country: countryFilter.length > 0 ? countryFilter : undefined,
			region: regionFilter.length > 0 ? regionFilter : undefined,
			producer: producerFilter.length > 0 ? producerFilter : undefined,
			farm: farmFilter.length > 0 ? farmFilter : undefined,
			roast_level: roastLevelFilter || undefined,
			roast_profile: roastProfileFilter || undefined,
			process: processFilter.length > 0 ? processFilter : undefined,
			variety: varietyFilter.length > 0 ? varietyFilter : undefined,
			min_price: minPrice ? parseFloat(minPrice) : undefined,
			max_price: maxPrice ? parseFloat(maxPrice) : undefined,
			min_weight: minWeight ? parseInt(minWeight) : undefined,
			max_weight: maxWeight ? parseInt(maxWeight) : undefined,
			min_elevation: minElevation ? parseInt(minElevation) : undefined,
			max_elevation: maxElevation ? parseInt(maxElevation) : undefined,
			min_cupping_score: minCuppingScore ? parseFloat(minCuppingScore) : undefined,
			max_cupping_score: maxCuppingScore ? parseFloat(maxCuppingScore) : undefined,
			in_stock_only: inStockOnly,
			is_decaf: isDecaf,
			is_single_origin: isSingleOrigin,
			tasting_notes_only: tastingNotesOnly,
			page: currentPage,
			per_page: perPage,
			sort_by: sortBy,
			sort_order: sortOrder
		};

		// Perform search
		const response = await api.search(params, fetch);

		if (!response.success) {
			throw error(500, {
				message: response.message || 'Search failed'
			});
		}

		return {
			searchResults: response.data || [],
			totalResults: response.pagination?.total_items || 0,
			totalPages: response.pagination?.total_pages || 0,
			searchParams: {
				searchQuery,
				tastingNotesQuery,
				smartQuery,
				roasterFilter,
				roasterLocationFilter,
				countryFilter,
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
				isSingleOrigin,
				tastingNotesOnly,
				sortBy,
				sortOrder,
				currentPage,
				perPage
			}
		};
	} catch (err) {
		console.error('Error loading search data:', err);
		throw error(500, {
			message: err instanceof Error ? err.message : 'An error occurred while performing search'
		});
	}
};
