import type { PageLoad } from './$types';
import { getUser } from '$lib/api/auth.remote';
import { db, type LocalSavedBean, type LocalCustomBean } from '$lib/db/localdb';
import { runGlobalSync } from '$lib/sync/syncManager.svelte';
import { browser } from '$app/environment';

export const load: PageLoad = async () => {
	const user = await getUser();

	// Trigger sync in background (client only)
	if (user && browser) {
		runGlobalSync({ silent: true });
	}

	let savedRecords: LocalSavedBean[] = [];
	let customRecords: LocalCustomBean[] = [];

	if (browser) {
		const [saved, custom] = await Promise.all([
			db.savedBeans
				.filter(b => !b.deletedAt && (b.ownerId === user?.id || !b.ownerId || !user))
				.toArray(),
			db.customBeans
				.filter(b => !b.deletedAt && (b.ownerId === user?.id || !b.ownerId || !user))
				.toArray()
		]);

		// Sort by createdAt descending
		saved.sort((a, b) => b.createdAt - a.createdAt);

		savedRecords = saved;
		customRecords = custom;
	}

	return {
		savedRecords,
		customRecords,
		totalSaved: savedRecords.length,
		userId: user?.id
	};
};
