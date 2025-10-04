import type { PageLoad } from './$types';
import type { VarietalDetails, CoffeeBean, PaginationInfo } from '$lib/api';
import { api } from '$lib/api';

export const load: PageLoad = async ({ params, url, fetch, parent }) => {
	const data = await parent();
	const varietalSlug = params.slug;

	// Get query parameters for search/filter options
	const page = parseInt(url.searchParams.get('page') || '1');
	const per_page = parseInt(url.searchParams.get('per_page') || '20');
	const sort_by = url.searchParams.get('sort_by') || 'name';
	const sort_order = url.searchParams.get('sort_order') || 'asc';

	try {
		// Load varietal details and beans in parallel
		const [varietalResponse, beansResponse] = await Promise.all([
			api.getVarietalDetails(varietalSlug, data?.currencyState?.selectedCurrency, fetch),
			api.getVarietalBeans(varietalSlug, { page, per_page, sort_by, sort_order, convert_to_currency: data?.currencyState?.selectedCurrency }, fetch)
		]);

		if (!varietalResponse.success || !varietalResponse.data) {
			throw new Error('Varietal not found');
		}

		if (!beansResponse.success) {
			throw new Error('Failed to load beans');
		}

		return {
			varietal: varietalResponse.data as VarietalDetails,
			beans: beansResponse.data as CoffeeBean[] || [],
			pagination: beansResponse.pagination as PaginationInfo || null,
			metadata: beansResponse.metadata || {},
			queryParams: {
				page,
				per_page,
				sort_by,
				sort_order
			}
		};
	} catch (error) {
		console.error('Error loading varietal details:', error);

		// Return error state
		return {
			varietal: null,
			beans: [],
			pagination: null,
			metadata: { error: error instanceof Error ? error.message : 'Failed to load varietal' },
			queryParams: {
				page,
				per_page,
				sort_by,
				sort_order
			}
		};
	}
};
