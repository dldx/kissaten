import { db, type TastingSession, setCurrentOwnerId, claimUnownedTastings } from '$lib/db/localdb';
import { pushTastings, pullTastings } from '$lib/api/tastings.remote';
import { getUserWithoutRedirect } from '$lib/api/auth.remote';
import { api, type CoffeeBean } from '$lib/api';
import { notifyUpdate } from '$lib/db/updates.svelte';

function getLastSyncKey(userId: string): string {
	return `kissaten_last_tasting_sync_${userId}`;
}

let isSyncing = false;

/**
 * Main sync function: pushes local changes then pulls remote changes
 * Scoped to the currently authenticated user.
 */
export async function syncTastings(): Promise<{
	success: boolean;
	error?: string;
	pushed?: number;
	pulledAdded?: number;
	pulledUpdated?: number;
	pulledDeleted?: number;
}> {
	if (isSyncing) {
		console.log('[tastingSync] Sync already in progress, skipping...');
		return { success: false, error: 'Sync already in progress' };
	}

	// Set syncing flag immediately to block concurrent invocations while we resolve the user session
	isSyncing = true;
	let pushedCount = 0;

	try {
		const user = await getUserWithoutRedirect();
		if (!user) {
			console.log('Skipping sync: user not authenticated');
			isSyncing = false;
			return { success: false, error: 'Not authenticated' };
		}

		const userId = user.id;

		// Set the current user context for local queries
		setCurrentOwnerId(userId);

		// Claim any unowned (guest) sessions for this user
		await claimUnownedTastings(userId);

		console.log(`Starting tasting sync for user ${userId}...`);

		// 1. Push local changes (only this user's records)
		try {
			pushedCount = await pushLocalChanges(userId);
		} catch (error) {
			console.error('Failed to push local changes:', error);
			// Continue to pull even if push fails
		}

		// 2. Pull remote changes
		let pullResult = { added: 0, updated: 0, deleted: 0 };
		try {
			pullResult = await pullRemoteChanges(userId);
		} catch (error) {
			console.error('Failed to pull remote changes:', error);
			throw error; // Re-throw to catch in main try-block
		}

		console.log('Tasting sync completed successfully');
		return {
			success: true,
			pushed: pushedCount,
			pulledAdded: pullResult.added,
			pulledUpdated: pullResult.updated,
			pulledDeleted: pullResult.deleted
		};
	} catch (error) {
		console.error('Tasting sync failed:', error);
		return { success: false, error: String(error) };
	} finally {
		isSyncing = false;
	}
}

/**
 * Find records modified locally since last sync and push them to server.
 * Only pushes records belonging to the specified user.
 */
async function pushLocalChanges(userId: string): Promise<number> {
	// Find all dirty records belonging to this user
	const dirtyRecords = await db.tastings
		.where('ownerId')
		.equals(userId)
		.filter(t => !t.syncedAt || (t.updatedAt || 0) > t.syncedAt)
		.toArray();

	if (dirtyRecords.length === 0) {
		console.log('No local changes to push');
		return 0;
	}

	console.log(`Pushing ${dirtyRecords.length} dirty records to server...`);

	const syncPayload = dirtyRecords.map(r => {
		// Skinny Sync for all beans (both public and custom)
		// Custom beans are now mirrored locally and rehydrated via the customBeans table
		const { beanData, ...skinnyRecord } = r;
		return {
			id: r.syncId!,
			data: JSON.stringify(skinnyRecord),
			updatedAt: r.updatedAt!,
			deletedAt: r.deletedAt || null
		};
	});

	// Push in batches to avoid server-side timeouts or other limits
	const BATCH_SIZE = 5;
	for (let i = 0; i < syncPayload.length; i += BATCH_SIZE) {
		const batch = syncPayload.slice(i, i + BATCH_SIZE);
		console.log(`Pushing batch ${Math.floor(i / BATCH_SIZE) + 1}/${Math.ceil(syncPayload.length / BATCH_SIZE)} (${batch.length} records)`);

		const result = await pushTastings(batch);

		if (result.success) {
			// Update syncedAt using non-blocking bulkPut (avoids holding rw transaction lock)
			const now = Date.now();
			const batchRecords = dirtyRecords.slice(i, i + BATCH_SIZE);
			const updated = batchRecords.map(record => ({ ...record, syncedAt: now }));
			await db.tastings.bulkPut(updated);
		} else {
			console.error(`Batch ${Math.floor(i / BATCH_SIZE) + 1} failed, stopping push`);
			break;
		}
	}

	console.log('Successfully pushed local changes');
	return dirtyRecords.length;
}

/**
 * Fetch records modified on server since last sync and merge them locally.
 * Uses a per-user sync cursor so switching accounts doesn't corrupt the timeline.
 */
async function pullRemoteChanges(userId: string): Promise<{ added: number; updated: number; deleted: number }> {
	const lastSyncKey = getLastSyncKey(userId);
	const lastSync = Number(localStorage.getItem(lastSyncKey) || '0');

	console.log(`Pulling remote changes since ${new Date(lastSync).toISOString()}...`);

	const remoteRecords = await pullTastings(lastSync);

	if (remoteRecords.length === 0) {
		console.log('No remote changes to pull');
		return { added: 0, updated: 0, deleted: 0 };
	}

	console.log(`Pulled ${remoteRecords.length} remote records`);

	// Identify beans that need rehydration (have path but no data)
	const beansToFetch = new Set<string>();
	const remoteSessions: { remote: any, data: TastingSession }[] = [];

	for (const remote of remoteRecords) {
		const data = JSON.parse(remote.data) as TastingSession;

		// Force strings back to Date objects (JSON.parse leaves them as strings)
		if (data.date && typeof data.date === 'string') {
			data.date = new Date(data.date);
		}

		remoteSessions.push({ remote, data });
		if (data.beanUrlPath && !data.beanData) {
			beansToFetch.add(data.beanUrlPath);
		}
	}

	// Batch fetch missing bean data
	const beanCache = new Map<string, CoffeeBean>();
	if (beansToFetch.size > 0) {
		console.log(`Rehydrating ${beansToFetch.size} unique beans...`);

		// First check local custom beans mirror
		const localCustomBeans = await db.customBeans
			.filter(b => beansToFetch.has(b.beanUrlPath))
			.toArray();

		for (const b of localCustomBeans) {
			beanCache.set(b.beanUrlPath, b.beanData);
			beansToFetch.delete(b.beanUrlPath);
		}

		// Then fetch remaining from public API
		if (beansToFetch.size > 0) {
			console.log(`Fetching ${beansToFetch.size} public beans from API...`);
			try {
				const response = await api.searchBeansByPaths(Array.from(beansToFetch));
				if (response.success && response.data) {
					response.data.forEach(bean => {
						if (bean.bean_url_path) beanCache.set(bean.bean_url_path, bean);
					});
				}
			} catch (error) {
				console.error('Failed to rehydrate beans during sync:', error);
			}
		}
	}

	// Pre-read all local records by syncId to avoid holding a long-lived rw transaction lock
	const localBySyncId = new Map(
		(await db.tastings.where('syncId').anyOf(remoteSessions.map(r => r.remote.id)).toArray())
			.map(t => [t.syncId!, t])
	);

	const toAdd: TastingSession[] = [];
	const toPut: TastingSession[] = [];
	const toDeleteIds: number[] = [];

	for (const { remote, data: remoteData } of remoteSessions) {
		const local = localBySyncId.get(remote.id);

		// If remote is deleted
		if (remote.deletedAt) {
			if (local) {
				console.log(`Deleting local record ${remote.id} (remote delete)`);
				toDeleteIds.push(local.id!);
			}
			continue;
		}

		// Rehydrate bean data from cache if missing
		if (remoteData.beanUrlPath && !remoteData.beanData) {
			const cachedBean = beanCache.get(remoteData.beanUrlPath);
			if (cachedBean) {
				remoteData.beanData = cachedBean;
			}
		}

		// Ensure date is a proper Date object for Dexie
		if (remoteData.date && typeof remoteData.date === 'string') {
			remoteData.date = new Date(remoteData.date);
		} else if (remoteData.date && typeof remoteData.date === 'number') {
			remoteData.date = new Date(remoteData.date);
		}

		if (remoteData.date instanceof Date && isNaN(remoteData.date.getTime())) {
			console.error(`CRITICAL: Remote record ${remote.id} has an INVALID date value, using current time as fallback`);
			remoteData.date = new Date();
		}

		// Ensure metadata matches the sync record
		remoteData.syncId = remote.id;
		remoteData.updatedAt = remote.updatedAt;
		remoteData.syncedAt = Date.now();
		remoteData.deletedAt = null;
		remoteData.ownerId = userId;

		if (!local) {
			toAdd.push(remoteData);
		} else if (remote.updatedAt > (local.updatedAt || 0)) {
			toPut.push({ ...remoteData, id: local.id });
		}
	}

	// Execute writes as quick non-blocking bulk operations
	if (toDeleteIds.length > 0) {
		await db.tastings.bulkDelete(toDeleteIds);
		console.log(`Deleted ${toDeleteIds.length} remote-deleted tastings`);
	}
	if (toAdd.length > 0) {
		await db.tastings.bulkAdd(toAdd);
		console.log(`Added ${toAdd.length} new remote tastings`);
	}
	if (toPut.length > 0) {
		await db.tastings.bulkPut(toPut);
		console.log(`Updated ${toPut.length} existing tastings`);
	}

	// 3. Update last sync timestamp only after a successful complete sync cycle
	localStorage.setItem(lastSyncKey, Date.now().toString());
	console.log('Successfully pulled and merged remote changes');
	notifyUpdate('tastingHistory');

	return {
		added: toAdd.length,
		updated: toPut.length,
		deleted: toDeleteIds.length
	};
}
