import { getSavedBeans } from "$lib/api/vault.remote";
import { getUserWithoutRedirect } from "$lib/api/auth.remote";
import { api } from "$lib/api";
import type { PageLoad } from "./$types";

export const load: PageLoad = async ({ fetch }) => {
	try {
		const [user, countriesResponse] = await Promise.all([
			getUserWithoutRedirect(),
			api.getCountries(fetch)
		]);

		const originOptions = countriesResponse.success && countriesResponse.data
			? countriesResponse.data.map((country) => ({
				value: country.country_code,
				text: country.country_name || country.country_code
			}))
			: [];

		if (user) {
			const beans = await getSavedBeans();
			return {
				savedBeanPaths: beans.map((b) => b.beanUrlPath),
				originOptions
			};
		}
		return {
			savedBeanPaths: [],
			originOptions
		};
	} catch (e) {
		return {
			savedBeanPaths: [],
			originOptions: []
		};
	}
};
