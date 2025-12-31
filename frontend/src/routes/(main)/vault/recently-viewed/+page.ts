import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
	const { currencyState } = await parent();

	return {
		currencyState
	};
};
