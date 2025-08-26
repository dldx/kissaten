import { api, type CoffeeBean } from '$lib/api.js';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ url, fetch }) => {
	try {
		// Extract search parameters from URL
		const urlParams = url.searchParams;
		const searchQuery = urlParams.get('q') || '';
		const roasterFilter = urlParams.get('roaster') || '';
		const countryFilter = urlParams.get('country') || '';
		const roastLevelFilter = urlParams.get('roast_level') || '';
		const roastProfileFilter = urlParams.get('roast_profile') || '';
		const processFilter = urlParams.get('process') || '';
		const varietyFilter = urlParams.get('variety') || '';
		const minPrice = urlParams.get('min_price') || '';
		const maxPrice = urlParams.get('max_price') || '';
		const minWeight = urlParams.get('min_weight') || '';
		const maxWeight = urlParams.get('max_weight') || '';
		const inStockOnly = urlParams.get('in_stock_only') === 'true';
		const sortBy = urlParams.get('sort_by') || 'name';
		const sortOrder = urlParams.get('sort_order') || 'asc';
		const currentPage = parseInt(urlParams.get('page') || '1');
		const perPage = 20;

		// Build search parameters
		const params = {
			query: searchQuery || undefined,
			roaster: roasterFilter || undefined,
			country: countryFilter || undefined,
			roast_level: roastLevelFilter || undefined,
			roast_profile: roastProfileFilter || undefined,
			process: processFilter || undefined,
			variety: varietyFilter || undefined,
			min_price: minPrice ? parseFloat(minPrice) : undefined,
			max_price: maxPrice ? parseFloat(maxPrice) : undefined,
			min_weight: minWeight ? parseInt(minWeight) : undefined,
			max_weight: maxWeight ? parseInt(maxWeight) : undefined,
			in_stock_only: inStockOnly,
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
				roasterFilter,
				countryFilter,
				roastLevelFilter,
				roastProfileFilter,
				processFilter,
				varietyFilter,
				minPrice,
				maxPrice,
				minWeight,
				maxWeight,
				inStockOnly,
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
