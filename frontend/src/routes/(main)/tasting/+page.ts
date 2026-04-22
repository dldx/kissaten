import { getSavedBeans } from "$lib/api/vault.remote";
import { getUserWithoutRedirect } from "$lib/api/auth.remote";
import type { PageLoad } from "./$types";

export const load: PageLoad = async () => {
	try {
		// Only attempt to fetch if user is authenticated
		const user = await getUserWithoutRedirect();

		if (user) {
			const beans = await getSavedBeans();
			return {
				savedBeanPaths: beans.map((b) => b.beanUrlPath)
			};
		}

		return {
			savedBeanPaths: []
		};
	} catch (e) {
		// Silent fail if other error
		return {
			savedBeanPaths: []
		};
	}
};
