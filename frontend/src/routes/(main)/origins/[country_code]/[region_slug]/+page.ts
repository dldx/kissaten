import { api } from '$lib/api';
import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageLoad = async ({ params, fetch }) => {
    const countryCode = params.country_code.toUpperCase();
    const regionSlug = params.region_slug;

    try {
        const response = await api.getRegionDetail(countryCode, regionSlug, fetch);
        if (response.success && response.data) {
            return {
                region: response.data,
                countryCode,
                regionSlug
            };
        } else {
            throw error(404, `Region '${regionSlug}' not found in country '${countryCode}'`);
        }
    } catch (e) {
        console.error('Error loading region detail:', e);
        throw error(404, `Region '${regionSlug}' not found in country '${countryCode}'`);
    }
};
