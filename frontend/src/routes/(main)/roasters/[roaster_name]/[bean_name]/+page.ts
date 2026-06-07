import { error } from '@sveltejs/kit';
import { api, type CoffeeBean } from '$lib/api.js';
import { currencyState } from '$lib/stores/currency.svelte.js';
import { browser } from '$app/environment';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const { roaster_name, bean_name } = params;

	// Handle custom beans from Dexie (local-first)
	if (roaster_name === 'custom') {
		// During SSR, we can't access Dexie, so we return null and let the client hydrate
		if (!browser) {
			return {
				bean: null,
				recommendations: [],
				isCustom: true
			};
		}

		try {
			const { db } = await import('$lib/db/localdb');
			const custom = await db.customBeans
				.where('syncId')
				.equals(bean_name)
				.first();

			if (custom) {
				return {
					bean: custom.beanData,
					recommendations: [],
					isCustom: true
				};
			}
		} catch (e) {
			console.warn('Failed to load custom bean from Dexie:', e);
		}
	}

	try {
		// The URL parameters are already in slug format (roaster_name and bean_name)
		// We can use them directly with the new slug-based endpoint
		let bean: CoffeeBean | null = null;
		let recommendations: CoffeeBean[] = [];

		try {
			// Use the new slug-based endpoint that works directly with URL slugs
			const beanResponse = await api.getBeanBySlug(roaster_name, bean_name, fetch, currencyState.selectedCurrency || undefined);

			if (beanResponse.success && beanResponse.data) {
				bean = beanResponse.data;

				// Get recommendations using the slug-based approach
				const recommendationsResponse = await api.getBeanRecommendationsBySlug(roaster_name, bean_name, 6, fetch, currencyState.selectedCurrency || undefined);
				recommendations = recommendationsResponse.success ? recommendationsResponse.data || [] : [];
			}
		} catch (e) {
			console.warn('Slug-based bean search failed:', e);
		}

		if (!bean && roaster_name !== 'custom') {
			throw error(404, {
				message: `Coffee bean "${bean_name}" from "${roaster_name}" not found`
			});
		}

		return {
			bean,
			recommendations,
			isCustom: false
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
