import { getSavedBeans } from "$lib/api/vault.remote";
import { getUser } from "$lib/api/auth.remote";
import type { PageLoad } from "./$types";

export const load: PageLoad = async () => {
	try {
		// Only attempt to fetch if user is authenticated
		await getUser();

		const beans = await getSavedBeans();
		return {
			savedBeanPaths: beans.map((b) => b.beanUrlPath)
		};
	} catch (e) {
		// Silent fail if not logged in or other error
		return {
			savedBeanPaths: []
		};
	}
};
