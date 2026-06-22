import type { PageLoad } from './$types';
import { browser } from '$app/environment';
import { getRecentlyViewedBeans, db } from '$lib/db/localdb';

export const load: PageLoad = async ({ parent }) => {
	const { currencyState } = await parent();

	let initialRecentlyViewed = [];
	let initialSavedBeans = [];

	if (browser) {
		const [recent, saved] = await Promise.all([
			getRecentlyViewedBeans(),
			db.savedBeans.filter(b => !b.deletedAt).toArray()
		]);

		// Deduplicate by path (keep most recent) and filter out entries without beanData
		const seenPaths = new Set<string>();
		initialRecentlyViewed = recent
			.filter(b => {
				if (!b.beanData || !b.beanUrlPath || seenPaths.has(b.beanUrlPath)) return false;
				seenPaths.add(b.beanUrlPath);
				return true;
			})
			.sort((a, b) => new Date(b.viewedAt).getTime() - new Date(a.viewedAt).getTime());

		initialSavedBeans = saved;
	}

	return {
		currencyState,
		initialRecentlyViewed,
		initialSavedBeans
	};
};
