import { error } from '@sveltejs/kit';
import { api, type CoffeeBean } from '$lib/api.js';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const { roaster_name, bean_name } = params;

	try {
		// The URL parameters are already in slug format (roaster_name and bean_name)
		// We can use them directly with the new slug-based endpoint
		let bean: CoffeeBean | null = null;
		let recommendations: CoffeeBean[] = [];

		try {
			// Use the new slug-based endpoint that works directly with URL slugs
			const beanResponse = await api.getBeanBySlug(roaster_name, bean_name);

			if (beanResponse.success && beanResponse.data) {
				bean = beanResponse.data;

				// Get recommendations using the slug-based approach
				const recommendationsResponse = await api.getBeanRecommendationsBySlug(roaster_name, bean_name, 6);
				recommendations = recommendationsResponse.success ? recommendationsResponse.data || [] : [];
			}
		} catch (e) {
			console.warn('Slug-based bean search failed:', e);
		}

		if (!bean) {
			throw error(404, {
				message: `Coffee bean "${bean_name}" from "${roaster_name}" not found`
			});
		}

		return {
			bean,
			recommendations,
		};
	} catch (err) {
		if (err && typeof err === 'object' && 'status' in err) {
			throw err;
		}
		throw error(500, {
			message: 'Failed to load coffee bean details'
		});
	}
};
