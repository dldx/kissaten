import { api } from '$lib/api';
import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageLoad = async ({ params, fetch }) => {
    const countryCode = params.country_code.toUpperCase();

    try {
        const [countryResponse, regionsResponse] = await Promise.all([
            api.getCountryDetail(countryCode, fetch),
            api.getCountryRegions(countryCode, fetch)
        ]);

        if (countryResponse.success && countryResponse.data && regionsResponse.success && regionsResponse.data) {
            return {
                country: countryResponse.data,
                regions: regionsResponse.data,
                countryCode
            };
        } else {
            throw error(404, `Country '${countryCode}' or its regions not found`);
        }
    } catch (e) {
        console.error('Error loading country detail:', e);
        throw error(404, `Country not found: ${countryCode}`);
    }
};
