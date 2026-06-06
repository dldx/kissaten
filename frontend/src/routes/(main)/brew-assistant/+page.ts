import type { PageLoad } from './$types';

export const load: PageLoad = async ({ url }) => {
	const beanUrlPath = url.searchParams.get('bean_url_path') || '';

	return {
		beanUrlPath
	};
};
