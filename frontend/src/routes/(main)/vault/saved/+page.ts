import type { PageLoad } from './$types';
import { getUser } from '$lib/api/auth.remote';
import { db } from '$lib/db/localdb';
import { runGlobalSync } from '$lib/sync/syncManager.svelte';
import { browser } from '$app/environment';

export const load: PageLoad = async ({ parent }) => {
	const user = await getUser();

	// Trigger sync in background (client only)
	if (user && browser) {
		runGlobalSync({ silent: true });
	}

	// We'll return empty initially or let the svelte file handle the dexie query
	// but to keep types consistent with existing structure:
	let beansWithNotes: any[] = [];
	let totalSaved = 0;

	if (browser) {
		const savedLocal = await db.savedBeans
			.filter(b => (b.ownerId === user?.id || !b.ownerId || !user))
			.toArray();

		// Sort by createdAt descending
		savedLocal.sort((a, b) => b.createdAt - a.createdAt);

		totalSaved = savedLocal.length;

		beansWithNotes = savedLocal
			.filter(b => b.beanData) // Only show rehydrated beans
			.map(b => ({
				...b.beanData,
				savedBeanId: b.syncId,
				notes: b.notes,
				savedAt: new Date(b.createdAt).toISOString(),
				updatedAt: new Date(b.updatedAt).toISOString()
			}));
	}

	return {
		beans: beansWithNotes,
		totalSaved: totalSaved,
		userId: user?.id
	};
};
