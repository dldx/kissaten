import { api, groupPodcastHits } from '$lib/api';
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
            const farm = response.data;

            // Search for podcast insights using farm name as a producer/farm filter and country as an origin filter
            const podcastsResponse = await api.searchPodcasts('', 10, { 
                    origin: farm.country_name,
                    producer: farm.farm_name 
                }, fetch)
                .catch(err => {
                    console.error('Error fetching podcast insights:', err);
                    return { success: false, data: { hits: [], total_hits: 0, query: '' } };
                });

            const finalPodcasts = podcastsResponse.success && podcastsResponse.data.hits
                ? groupPodcastHits(podcastsResponse.data.hits).slice(0, 3)
                : [];

            return {
                farm,
                countryCode,
                regionSlug,
                farmSlug,
                podcasts: finalPodcasts
            };
        } else {
            throw error(404, `Farm '${farmSlug}' not found in region '${regionSlug}', country '${countryCode}'`);
        }
    } catch (e) {
        console.error('Error loading farm detail:', e);
        throw error(404, `Farm '${farmSlug}' not found in region '${regionSlug}', country '${countryCode}'`);
    }
};
