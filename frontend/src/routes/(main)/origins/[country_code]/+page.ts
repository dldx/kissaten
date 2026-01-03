import { api } from '$lib/api';
import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageLoad = async ({ params, fetch }) => {
    const countryCode = params.country_code.toUpperCase();

    try {
        const response = await api.getCountryDetail(countryCode, fetch);
        if (response.success && response.data) {
            return {
                country: response.data
            };
        } else {
            throw error(404, `Country not found: ${countryCode}`);
        }
    } catch (e) {
        console.error('Error loading country detail:', e);
        throw error(404, `Country not found: ${countryCode}`);
    }
};
