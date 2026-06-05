import type { PageLoad } from './$types';
import { browser } from '$app/environment';
import { getRecentlyViewedBeans, db } from '$lib/db/localdb';

export const load: PageLoad = async ({ parent }) => {
	const { currencyState } = await parent();

	let initialRecentlyViewed = [];
	let initialSavedBeans = [];

	if (browser) {
		[initialRecentlyViewed, initialSavedBeans] = await Promise.all([
			getRecentlyViewedBeans(),
			db.savedBeans.toArray()
		]);
	}

	return {
		currencyState,
		initialRecentlyViewed,
		initialSavedBeans
	};
};
