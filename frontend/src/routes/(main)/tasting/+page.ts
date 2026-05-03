import { getSavedBeans } from "$lib/api/vault.remote";
import { getUserWithoutRedirect } from "$lib/api/auth.remote";
import { api } from "$lib/api";
import type { PageLoad } from "./$types";

export const load: PageLoad = async ({ url, fetch }) => {
	const preselectedBeanPath = url.searchParams.get('bean');
	console.log("[Tasting Load] preselectedBeanPath:", preselectedBeanPath);
	let preselectedBean = null;

	if (preselectedBeanPath) {
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

	try {
		// Only attempt to fetch if user is authenticated
		const user = await getUserWithoutRedirect();

		if (user) {
			const beans = await getSavedBeans();
			return {
				savedBeanPaths: beans.map((b) => b.beanUrlPath),
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
