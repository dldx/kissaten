import { api, type Country, type CountryCode } from '$lib/api.js';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
	try {
		const [countriesResponse] = await Promise.all([
			api.getCountries(fetch),
		]);

		if (!countriesResponse.success || !countriesResponse.data) {
			throw error(500, {
				message: countriesResponse.message || 'Failed to load countries'
			});
		}

		return {
			countries: countriesResponse.data,
		};
	} catch (err) {
		console.error('Error loading countries data:', err);
		throw error(500, {
			message: err instanceof Error ? err.message : 'An error occurred while loading countries data'
		});
	}
};
