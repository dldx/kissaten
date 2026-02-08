import { api } from '$lib/api';
import type { PageLoad } from './$types';
import { error } from '@sveltejs/kit';

export const load: PageLoad = async ({ params, fetch, parent }) => {
    const data = await parent();
    const countryCode = params.country_code.toUpperCase();
    const regionSlug = params.region_slug;
    const farmSlug = params.farm_slug;

    try {
        const response = await api.getFarmDetail(countryCode, regionSlug, farmSlug, data?.currencyState?.selectedCurrency, fetch);
        if (response.success && response.data) {
            return {
                farm: response.data,
                countryCode,
                regionSlug,
                farmSlug
            };
        } else {
            throw error(404, `Farm '${farmSlug}' not found in region '${regionSlug}', country '${countryCode}'`);
        }
    } catch (e) {
        console.error('Error loading farm detail:', e);
        throw error(404, `Farm '${farmSlug}' not found in region '${regionSlug}', country '${countryCode}'`);
    }
};
