import type { PageLoad } from './$types';

export const load: PageLoad = async ({ parent }) => {
    // Get data from parent layout
    const parentData = await parent();
    return parentData;
};
