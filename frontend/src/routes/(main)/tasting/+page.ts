import { getSavedBeans } from "$lib/api/vault.remote";
import { getCustomBeans } from "$lib/api/custom_beans.remote";
import { getUserWithoutRedirect } from "$lib/api/auth.remote";
import { api } from "$lib/api";
import { browser } from "$app/environment";
import type { PageLoad } from "./$types";

export const load: PageLoad = async ({ url, fetch }) => {
	const preselectedBeanPath = url.searchParams.get('bean');
	console.log("[Tasting Load] preselectedBeanPath:", preselectedBeanPath);
	let preselectedBean = null;

	if (preselectedBeanPath) {
		if (preselectedBeanPath.startsWith('/custom/')) {
			// Handle custom beans from Dexie (local-first)
			if (browser) {
				try {
					const { db } = await import('$lib/db/localdb');
					const syncId = preselectedBeanPath.replace('/custom/', '');
					const custom = await db.customBeans
						.where('syncId')
						.equals(syncId)
						.first();

					if (custom) {
						preselectedBean = custom.beanData;
						console.log("[Tasting Load] Found custom bean in Dexie:", preselectedBean.name);
					}
				} catch (e) {
					console.warn('[Tasting Load] Failed to load custom bean from Dexie:', e);
				}
			}
			
			// Fallback: if not in browser or not in Dexie, try fetching from remote custom beans
			if (!preselectedBean) {
				try {
					const customBeans = await getCustomBeans();
					const match = customBeans.find(b => b.bean_url_path === preselectedBeanPath);
					if (match) {
						preselectedBean = match;
						console.log("[Tasting Load] Found custom bean in Remote:", preselectedBean.name);
					}
				} catch (e) {
					console.error("[Tasting Load] Failed to load preselected custom bean from remote:", e);
				}
			}
		} else {
			try {
				// Pass empty params object since searchBeansByPaths expects 3 arguments when fetch is provided
				const response = await api.searchBeansByPaths([preselectedBeanPath], {}, fetch);
				console.log("[Tasting Load] API response:", response);

				if (response.success && response.data && response.data.length > 0) {
					preselectedBean = response.data[0];
					console.log("[Tasting Load] Found bean:", preselectedBean.name);
				} else {
					preselectedBean = null;
					console.log("[Tasting Load] Bean not found in API response");
				}
			} catch (e) {
				console.error("[Tasting Load] Failed to load preselected bean:", e);
			}
		}
	}

	try {
		// Only attempt to fetch if user is authenticated
		const user = await getUserWithoutRedirect();

		if (user) {
			const [beans, customBeans] = await Promise.all([
				getSavedBeans(),
				getCustomBeans()
			]);
			return {
				savedBeanPaths: [
					...beans.map((b) => b.beanUrlPath),
					...customBeans.map((b) => b.bean_url_path || `/custom/${b.id}`)
				],
				preselectedBean
			};
		}

		return {
			savedBeanPaths: [],
			preselectedBean
		};
	} catch (e) {
		// Silent fail if other error
		return {
			savedBeanPaths: [],
			preselectedBean
		};
	}
};
