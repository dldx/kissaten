import { error } from '@sveltejs/kit';
import { api, type CoffeeBean } from '$lib/api.js';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params, fetch }) => {
	const { roaster_name, bean_name } = params;

	try {
		// Convert URL-friendly names back to search terms
		const roasterSearchTerm = roaster_name.replace(/_/g, ' ');
		const beanSearchTerm = bean_name.replace(/_/g, ' ');

		// Convert roaster name to directory format (same as used in data structure)
		function getRoasterDirectoryName(roasterName: string): string {
			return roasterName.toLowerCase()
				.replace(/\s+/g, '_')
				.replace(/[^a-z0-9_]/g, '')
				.replace(/_{2,}/g, '_')
				.replace(/^_|_$/g, '');
		}

		// Extract filename from full path (remove .json extension)
		function extractFilenameFromPath(fullPath: string): string {
			const parts = fullPath.split('/');
			const filename = parts[parts.length - 1];
			return filename.replace('.json', '');
		}

		// Try to find the bean using the direct filename approach
		const roasterDirName = getRoasterDirectoryName(roasterSearchTerm);

		// First, get all bean files for this roaster to find the best filename match
		let roasterBeans;
		try {
			const roasterBeansResponse = await fetch(`http://localhost:8000/api/v1/roasters/${roasterDirName}/beans`);
			if (roasterBeansResponse.ok) {
				const data = await roasterBeansResponse.json();
				roasterBeans = data.data || [];
			}
		} catch (e) {
			console.warn('Could not fetch roaster beans:', e);
		}

		// Try to find the best matching bean file by comparing the URL bean_name with extracted filenames
		let matchingBean = null;
		let beanFilename = null;

		if (roasterBeans && roasterBeans.length > 0) {
			// Look for filename matches
			const normalizedBeanSearch = bean_name.toLowerCase();

			// Try to find a bean where the filename (without .json) matches the URL bean_name
			matchingBean = roasterBeans.find((bean: any) => {
				if (bean.filename) {
					const extractedFilename = extractFilenameFromPath(bean.filename);
					return extractedFilename.toLowerCase() === normalizedBeanSearch;
				}
				return false;
			});

			// If no exact filename match, try partial matches in bean names
			if (!matchingBean) {
				const normalizedNameSearch = beanSearchTerm.toLowerCase();
				matchingBean = roasterBeans.find((bean: any) =>
					bean.name.toLowerCase().includes(normalizedNameSearch) ||
					normalizedNameSearch.includes(bean.name.toLowerCase().substring(0, 10))
				);
			}

			if (matchingBean && matchingBean.filename) {
				beanFilename = extractFilenameFromPath(matchingBean.filename);
			}
		}

		// If we found a matching bean file, get its full details and recommendations
		let bean: CoffeeBean | null = null;
		let recommendations: CoffeeBean[] = [];

		if (beanFilename) {
			try {
				const beanResponse = await api.getBeanByFilename(roasterDirName, beanFilename);
				if (beanResponse.success && beanResponse.data) {
					bean = beanResponse.data;

					// Get recommendations
					const recommendationsResponse = await api.getBeanRecommendationsByFilename(roasterDirName, beanFilename, 6);
					recommendations = recommendationsResponse.success ? recommendationsResponse.data || [] : [];
				}
			} catch (e) {
				console.warn('Could not fetch bean by filename:', e);
			}
		}

		// Fallback to search-based approach if file-based approach failed
		if (!bean) {
			try {
				const searchResponse = await api.search({
					roaster: roasterSearchTerm,
					query: beanSearchTerm,
					per_page: 1
				});

				if (searchResponse.success && searchResponse.data && searchResponse.data.length > 0) {
					bean = searchResponse.data[0];

					// Get recommendations using the traditional ID-based approach
					const recommendationsResponse = await api.getBeanRecommendations(bean.id, 6);
					recommendations = recommendationsResponse.success ? recommendationsResponse.data || [] : [];
				}
			} catch (e) {
				console.warn('Search fallback failed:', e);
			}
		}

		if (!bean) {
			throw error(404, {
				message: `Coffee bean "${bean_name}" from "${roaster_name}" not found`
			});
		}

		return {
			bean,
			recommendations,
			roaster_name: roasterSearchTerm,
			bean_name: beanSearchTerm,
			bean_filename: beanFilename,
			roaster_directory: roasterDirName
		};
	} catch (err) {
		if (err && typeof err === 'object' && 'status' in err) {
			throw err;
		}
		throw error(500, {
			message: 'Failed to load coffee bean details'
		});
	}
};
