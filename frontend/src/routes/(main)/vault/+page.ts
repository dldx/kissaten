import type { PageLoad } from './$types';
import { getSavedBeans } from '$lib/api/vault.remote';
import { api } from '$lib/api';

export const load: PageLoad = async ({ fetch }) => {
	const savedBeans = await getSavedBeans();

	// Extract bean_url_paths from saved beans
	const beanUrlPaths = savedBeans.map(bean => bean.beanUrlPath);

	// Fetch full bean details using search_beans_by_paths endpoint
	let beans = [];
	if (beanUrlPaths.length > 0) {
		const response = await api.searchBeansByPaths(beanUrlPaths, {}, fetch);
		beans = response.data || [];
	}

	// Merge saved bean metadata (notes, saved date) with full bean details
	const beansWithNotes = beans.map(bean => {
		const savedBean = savedBeans.find(sb => sb.beanUrlPath === bean.bean_url_path);
		return {
			...bean,
			savedBeanId: savedBean?.id,
			notes: savedBean?.notes,
			savedAt: savedBean?.createdAt
		};
	});

	return {
		beans: beansWithNotes,
		totalSaved: savedBeans.length
	};
};
