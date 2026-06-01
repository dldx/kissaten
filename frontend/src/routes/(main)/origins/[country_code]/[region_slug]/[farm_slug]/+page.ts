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
            // We return the promise directly so SvelteKit can stream it without delaying the main page load
            const podcastsPromise = api.searchPodcasts('', 10, {
                origin: farm.country_name,
                producer: farm.farm_name
            }, fetch)
                .then((resp) => {
                    if (resp.success && resp.data.hits) {
                        return groupPodcastHits(resp.data.hits);
                    }
                    return [] as GroupedPodcastHit[];
                })
                .catch(err => {
                    console.error('Error fetching podcast insights:', err);
                    return [] as GroupedPodcastHit[];
                });

            return {
                farm,
                countryCode,
                regionSlug,
                farmSlug,
                podcastsStream: podcastsPromise
            };
        } else {
            throw error(404, `Farm '${farmSlug}' not found in region '${regionSlug}', country '${countryCode}'`);
        }
    } catch (e) {
        console.error('Error loading farm detail:', e);
        throw error(404, `Farm '${farmSlug}' not found in region '${regionSlug}', country '${countryCode}'`);
    }
};
