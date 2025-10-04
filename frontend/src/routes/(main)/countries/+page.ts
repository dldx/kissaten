import { api, type Country, type CountryCode } from '$lib/api.js';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	try {
		const [countriesResponse, countryCodesResponse] = await Promise.all([
			api.getCountries(fetch),
			api.getCountryCodes(fetch)
		]);

		if (!countriesResponse.success || !countriesResponse.data) {
			throw error(500, {
				message: countriesResponse.message || 'Failed to load countries'
			});
		}

		if (!countryCodesResponse.success || !countryCodesResponse.data) {
			throw error(500, {
				message: countryCodesResponse.message || 'Failed to load country codes'
			});
		}

		return {
			countries: countriesResponse.data,
			countryCodes: countryCodesResponse.data
		};
	} catch (err) {
		console.error('Error loading countries data:', err);
		throw error(500, {
			message: err instanceof Error ? err.message : 'An error occurred while loading countries data'
		});
	}
};
