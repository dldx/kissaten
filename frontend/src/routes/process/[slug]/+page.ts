import { api } from '$lib/api';
import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageLoad = async ({ params, fetch, url }) => {
	const { slug } = params;

	// Get query parameters for bean list
	const page = parseInt(url.searchParams.get('page') || '1', 10);
	const per_page = parseInt(url.searchParams.get('per_page') || '20', 10);
	const sort_by = url.searchParams.get('sort_by') || 'name';
	const sort_order = url.searchParams.get('sort_order') || 'asc';

	try {
		// Load process details and beans in parallel
		const [processResponse, beansResponse] = await Promise.all([
			api.getProcessDetails(slug, fetch),
			api.getProcessBeans(slug, { page, per_page, sort_by, sort_order }, fetch)
		]);

		if (!processResponse.success || !processResponse.data) {
			throw error(404, `Process "${slug}" not found`);
		}

		if (!beansResponse.success || !beansResponse.data) {
			throw error(500, 'Failed to load coffee beans for this process');
		}

		return {
			process: processResponse.data,
			beans: beansResponse.data,
			pagination: beansResponse.pagination,
			metadata: beansResponse.metadata,
			// Pass through query params for client-side state
			queryParams: {
				page,
				per_page,
				sort_by,
				sort_order
			}
		};
	} catch (err) {
		console.error('Error loading process page:', err);
		if (err instanceof Error && err.message.includes('404')) {
			throw error(404, `Process "${slug}" not found`);
		}
		throw error(500, 'Failed to load process details');
	}
};
