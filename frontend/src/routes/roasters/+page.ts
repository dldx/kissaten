import { api, type Roaster } from '$lib/api.js';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	try {
		const response = await api.getRoasters(fetch);

		if (!response.success || !response.data) {
			throw error(500, {
				message: response.message || 'Failed to load roasters'
			});
		}

		return {
			roasters: response.data
		};
	} catch (err) {
		console.error('Error loading roasters data:', err);
		throw error(500, {
			message: err instanceof Error ? err.message : 'An error occurred while loading roasters data'
		});
	}
};
