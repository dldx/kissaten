import { api } from '$lib/api';
import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageLoad = async ({ params, fetch }) => {
    const countryCode = params.country_code.toUpperCase();
    const regionSlug = params.region_slug;

    try {
        const [regionRes, farmsRes] = await Promise.all([
            api.getRegionDetail(countryCode, regionSlug, fetch),
            api.getRegionFarms(countryCode, regionSlug, fetch)
        ]);

        if (regionRes.success && regionRes.data && farmsRes.success && farmsRes.data) {
            return {
                region: regionRes.data,
                farms: farmsRes.data,
                countryCode,
                regionSlug
            };
        } else {
            throw error(404, `Region '${regionSlug}' not found in country '${countryCode}'`);
        }
    } catch (e) {
        console.error('Error loading region farms:', e);
        throw error(404, `Region '${regionSlug}' not found in country '${countryCode}'`);
    }
};
