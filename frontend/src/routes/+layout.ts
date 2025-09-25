import { currencyState } from '$lib/stores/currency.svelte.js';
import { api } from '$lib/api';

// Initialize the currency store so it's available everywhere
export async function load({ fetch }) {
	// The currency store is already initialized in its constructor
	// This ensures it's loaded at the root layout level
	const [countriesResponse, roastersResponse, roasterLocationsResponse] = await Promise.all([
		api.getCountries(fetch),
		api.getRoasters(fetch),
		api.getRoasterLocations(fetch)
	]);

	const originOptions =
		countriesResponse.success && countriesResponse.data
			? countriesResponse.data.map((country) => ({
				value: country.country_code,
				text: country.country_name || country.country_code
			}))
			: [];

	const allRoasters = roastersResponse.success && roastersResponse.data ? roastersResponse.data : [];

	const roasterLocationOptions =
		roasterLocationsResponse.success && roasterLocationsResponse.data
			? roasterLocationsResponse.data.map((location) => ({
				value: location.code,
				text: `${location.code} - ${location.location} (${location.roaster_count})`
			}))
			: [];
	return {
		currencyState,
		originOptions,
		allRoasters,
		roasterLocationOptions
	};
}