import { currencyState } from '$lib/stores/currency.svelte.js';
import { api } from '$lib/api';
import type { UserDefaults } from '$lib/types/userDefaults';

// Initialize the currency store so it's available everywhere
export async function load({ fetch, parent, data }) {
	// Pick up parent (root) layout data so it propagates to children.
	const parentData = await parent();

	// `data` is the sibling `+layout.server.ts` return — `currency` (cookie)
	// and `userDefaults.roasterLocations` (server-loaded via the
	// `getUserDefaultRoasterLocations` remote query). Layout data merges
	// down to children automatically, but we surface `userDefaults`
	// explicitly so the type is non-optional for consumers.
	const userDefaults: UserDefaults = data.userDefaults ?? { roasterLocations: [] };

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
				text: `${location.location} (${location.roaster_count})`
			}))
			: [];
	return {
		...parentData,
		currencyState,
		originOptions,
		allRoasters,
		roasterLocationOptions,
		userDefaults
	};
}
