import { api } from '$lib/api';
import type { LayoutLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: LayoutLoad = async ({ params, fetch }) => {
    const countryCode = params.country_code.toUpperCase();
    const regionSlug = params.region_slug;

    try {
        const [regionResponse, farmsResponse] = await Promise.all([
            api.getRegionDetail(countryCode, regionSlug, fetch),
            api.getRegionFarms(countryCode, regionSlug, fetch)
        ]);

        if (regionResponse.success && regionResponse.data && farmsResponse.success && farmsResponse.data) {
            return {
                region: regionResponse.data,
                farms: farmsResponse.data,
                countryCode,
                regionSlug
            };
        } else {
            throw error(404, `Region '${regionSlug}' or its farms not found in country '${countryCode}'`);
        }
    } catch (e) {
        console.error('Error loading region detail:', e);
        throw error(404, `Region '${regionSlug}' not found in country '${countryCode}'`);
    }
};
