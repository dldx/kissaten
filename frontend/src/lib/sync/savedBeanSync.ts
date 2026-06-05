import { db, type LocalSavedBean } from '$lib/db/localdb';
import { pullSavedBeans } from '$lib/api/vault.remote';
import { getUserWithoutRedirect } from '$lib/api/auth.remote';
import { api, type CoffeeBean } from '$lib/api';
import { notifyUpdate } from '$lib/db/updates.svelte';

function getLastSyncKey(userId: string): string {
	return `kissaten_last_saved_bean_sync_${userId}`;
}

let isSyncing = false;

/**
 * Sync saved beans from server to local database.
 */
export async function syncSavedBeans(): Promise<{
	success: boolean;
	error?: string;
	pulledAdded?: number;
	pulledUpdated?: number;
}> {
	if (isSyncing) {
		console.log('[savedBeanSync] Sync already in progress, skipping...');
		return { success: false, error: 'Sync already in progress' };
	}

	// Set syncing flag immediately to block concurrent invocations while we resolve the user session
	isSyncing = true;

	try {
		// Ensure this only runs on the client
		if (typeof window === 'undefined') {
			isSyncing = false;
			return { success: false, error: 'Cannot sync on server' };
		}

		const user = await getUserWithoutRedirect();
		if (!user) {
			console.log('Skipping saved beans sync: user not authenticated');
			isSyncing = false;
			return { success: false, error: 'Not authenticated' };
		}

		const userId = user.id;
		console.log(`Starting saved beans sync for user ${userId}...`);

		// Pull remote changes
		const pullResult = await pullRemoteChanges(userId);

		console.log('Saved beans sync completed successfully');
		return {
			success: true,
			pulledAdded: pullResult.added,
			pulledUpdated: pullResult.updated
		};
	} catch (error) {
		console.error('Saved beans sync failed:', error);
		return { success: false, error: String(error) };
	} finally {
		isSyncing = false;
	}
}

async function pullRemoteChanges(userId: string): Promise<{ added: number; updated: number }> {
	const lastSyncKey = getLastSyncKey(userId);
	const lastSync = Number(localStorage.getItem(lastSyncKey) || '0');

	console.log(`Pulling remote saved beans since ${new Date(lastSync).toISOString()}...`);

	const remoteRecords = await pullSavedBeans(lastSync);

	if (remoteRecords.length === 0) {
		console.log('No remote saved bean changes to pull');
		localStorage.setItem(lastSyncKey, Date.now().toString());
		return { added: 0, updated: 0 };
	}

	console.log(`Pulled ${remoteRecords.length} remote saved beans`);

	// Identify beans that need rehydration (no data in local DB yet)
	const beansToFetch = new Set<string>();
	for (const remote of remoteRecords) {
		const local = await db.savedBeans.where('syncId').equals(remote.id).first();
		if (!local || !local.beanData) {
			beansToFetch.add(remote.beanUrlPath);
		}
	}

	// Batch fetch missing bean data
	const beanCache = new Map<string, CoffeeBean>();
	if (beansToFetch.size > 0) {
		console.log(`Rehydrating ${beansToFetch.size} unique beans for vault...`);

		// Check local custom beans mirror first
		const localCustomBeans = await db.customBeans
			.filter(b => beansToFetch.has(b.beanUrlPath))
			.toArray();

		for (const b of localCustomBeans) {
			beanCache.set(b.beanUrlPath, b.beanData);
			beansToFetch.delete(b.beanUrlPath);
		}

		// fetch remaining from public API
		if (beansToFetch.size > 0) {
			try {
				const response = await api.searchBeansByPaths(Array.from(beansToFetch));
				if (response.success && response.data) {
					response.data.forEach(bean => {
						if (bean.bean_url_path) beanCache.set(bean.bean_url_path, bean);
					});
				}
			} catch (error) {
				console.error('Failed to rehydrate beans during saved bean sync:', error);
			}
		}
	}

	let added = 0;
	let updated = 0;

	await db.transaction('rw', db.savedBeans, async () => {
		for (const remote of remoteRecords) {
			const local = await db.savedBeans.where('syncId').equals(remote.id).first();

			// Handle potentially deleted records if we had soft delete, but vault uses hard delete
			// For now we assume they are alive if they are in the result of pullSavedBeans

			const cachedBean = beanCache.get(remote.beanUrlPath);

			const data: LocalSavedBean = {
				syncId: remote.id,
				beanUrlPath: remote.beanUrlPath,
				notes: remote.notes,
				createdAt: remote.createdAt,
				updatedAt: remote.updatedAt,
				deletedAt: null,
				syncedAt: Date.now(),
				ownerId: userId,
				beanData: cachedBean || local?.beanData
			};

			if (!local) {
				console.log(`Adding new remote saved bean ${remote.id}`);
				await db.savedBeans.add(data);
				added++;
			} else if (remote.updatedAt > (local.updatedAt || 0)) {
				console.log(`Updating local saved bean ${remote.id}`);
				await db.savedBeans.put({ ...data, id: local.id });
				updated++;
			} else {
				console.log(`Skipping remote saved bean ${remote.id} (local is same or newer)`);
			}
		}
	});

	localStorage.setItem(lastSyncKey, Date.now().toString());
	notifyUpdate('savedBeans');

	return { added, updated };
}
