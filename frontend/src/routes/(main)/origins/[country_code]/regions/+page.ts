import { api } from '$lib/api';
import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageLoad = async ({ params, fetch }) => {
    const countryCode = params.country_code.toUpperCase();

    try {
        const [countryRes, regionsRes] = await Promise.all([
            api.getCountryDetail(countryCode, fetch),
            api.getCountryRegions(countryCode, fetch)
        ]);

        if (countryRes.success && countryRes.data && regionsRes.success && regionsRes.data) {
            return {
                country: countryRes.data,
                regions: regionsRes.data
            };
        } else {
            throw error(404, `Country not found: ${countryCode}`);
        }
    } catch (e) {
        console.error('Error loading country regions:', e);
        throw error(404, `Country not found: ${countryCode}`);
    }
};
