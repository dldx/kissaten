import { api } from '$lib/api';
import type { LayoutLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: LayoutLoad = async ({ params, fetch }) => {
    const countryCode = params.country_code.toUpperCase();
    const regionSlug = params.region_slug;

    try {
        const regionResponse = await api.getRegionDetail(countryCode, regionSlug, fetch);

        if (regionResponse.success && regionResponse.data) {
            return {
                region: regionResponse.data,
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
