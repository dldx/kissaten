import type { PageLoad } from './$types';
import { getAllLocalCustomBeans } from '$lib/db/localdb';
import { runGlobalSync } from '$lib/sync/syncManager.svelte';
import { browser } from '$app/environment';
import { getUser } from '$lib/api/auth.remote';

export const load: PageLoad = async () => {
    const user = await getUser();

    // Trigger sync in background (client only)
    if (user && browser) {
        runGlobalSync({ silent: true });
    }

    let beans = [];
    if (browser) {
        beans = await getAllLocalCustomBeans();
    }

    return {
        beans,
        userId: user?.id
    };
};
