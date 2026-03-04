import type { PageLoad } from './$types';
import { getSavedBeans } from '$lib/api/vault.remote';
import { getUser } from '$lib/api/auth.remote';
import { api, type CoffeeBean } from '$lib/api';

export const load: PageLoad = async ({ fetch, url, params, parent }) => {
	await getUser();

	const { currencyState } = await parent();
	let savedBeans = await getSavedBeans();

	// Sort by saved date (createdAt) descending - newest first
	savedBeans = [...savedBeans].sort((a, b) => {
		const dateA = new Date(a.createdAt).getTime();
		const dateB = new Date(b.createdAt).getTime();
		return dateB - dateA;
	});

	// Extract bean_url_paths from saved beans
	const beanUrlPaths = savedBeans.map(bean => bean.beanUrlPath);

	const page = Number(url.searchParams.get('page')) || 1;
	const per_page = Number(url.searchParams.get('per_page')) || 21;

	// Slice the paths list to only include what's needed for the current page
	const start = (page - 1) * per_page;
	const end = start + per_page;
	const pagedPaths = beanUrlPaths.slice(start, end);

	// Fetch full bean details using search_beans_by_paths endpoint
	let beans: CoffeeBean[] = [];
	let pagination = null;

	let searchParams = {
		page: 1, // We already sliced the paths, so we treat this as the first page of the subset
		per_page: per_page,
		sort_by: 'path_order',
		convert_to_currency: currencyState.selectedCurrency,
		...params
	};

	if (pagedPaths.length > 0) {
		const response = await api.searchBeansByPaths(pagedPaths, searchParams, fetch);
		beans = response.data || [];

		// Reconstruct the pagination object based on the full list of saved beans
		pagination = {
			page,
			per_page,
			total_items: savedBeans.length,
			total_pages: Math.ceil(savedBeans.length / per_page),
			has_next: end < savedBeans.length,
			has_previous: page > 1
		};
	}

	// Merge saved bean metadata (notes, saved date) with full bean details
	const beansWithNotes = beans.map(bean => {
		const savedBean = savedBeans.find(sb => sb.beanUrlPath === bean.bean_url_path);
		return {
			...bean,
			savedBeanId: savedBean?.id,
			notes: savedBean?.notes,
			savedAt: savedBean?.createdAt,
			updatedAt: savedBean?.updatedAt
		};
	});

	return {
		beans: beansWithNotes,
		pagination,
		totalSaved: savedBeans.length
	};
};
