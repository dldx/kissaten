import { api, groupPodcastHits } from '$lib/api';
import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageLoad = async ({ params, fetch, url, parent }) => {
	const data = await parent();
	const { slug } = params;

	// Get query parameters for bean list
	const page = parseInt(url.searchParams.get('page') || '1', 10);
	const per_page = parseInt(url.searchParams.get('per_page') || '20', 10);
	const sort_by = url.searchParams.get('sort_by') || 'date_added';
	const sort_order = url.searchParams.get('sort_order') || 'desc';


	try {
		// Load process details, beans, and podcast insights in parallel
		const [processResponse, beansResponse] = await Promise.all([
			api.getProcessDetails(slug, data?.currencyState?.selectedCurrency, fetch),
			api.getProcessBeans(slug, { page, per_page, sort_by, sort_order, convert_to_currency: data?.currencyState?.selectedCurrency }, fetch)
		]);

		if (!processResponse.success || !processResponse.data) {
			throw error(404, `Process "${slug}" not found`);
		}

		if (!beansResponse.success || !beansResponse.data) {
			throw error(500, 'Failed to load coffee beans for this process');
		}

		// Search for podcast insights separately to avoid blocking the page if it fails or has no results
		// We use the common name (canonical) from process details for the filter
		const podcastsResponse = await api.searchPodcasts('', 10, { process: processResponse.data.name }, fetch)
			.catch(err => {
				console.error('Error fetching podcast insights:', err);
				return { success: false, data: { hits: [], total_hits: 0, query: '' } };
			});

		const finalPodcasts = podcastsResponse.success && podcastsResponse.data.hits
			? groupPodcastHits(podcastsResponse.data.hits).slice(0, 3)
			: [];

		return {
			process: processResponse.data,
			beans: beansResponse.data,
			pagination: beansResponse.pagination,
			metadata: beansResponse.metadata,
			podcasts: finalPodcasts,
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
