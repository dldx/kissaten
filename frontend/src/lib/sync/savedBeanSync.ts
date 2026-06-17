import { db, type LocalSavedBean, setCurrentOwnerId, claimUnownedSavedBeans } from '$lib/db/localdb';
import { getSavedBeans, saveBean, unsaveBean, updateBeanNotes } from '$lib/api/vault.remote';
import { getUserWithoutRedirect } from '$lib/api/auth.remote';
import { api, type CoffeeBean } from '$lib/api';
import { notifyUpdate } from '$lib/db/updates.svelte';

export type SavedBeanSyncOptions = {
	/** No-op for saved beans: this sync already does a full reconciliation on
	 *  every run (it pulls the whole remote list). Kept for API symmetry with
	 *  the other sync functions and for future use. */
	forceFullSync?: boolean;
};

let isSyncing = false;

/** Race a promise against a timeout. Rejects if the promise doesn't resolve in time. */
function withTimeout<T>(promise: Promise<T>, ms: number, label: string): Promise<T> {
	return Promise.race([
		promise,
		new Promise<never>((_, reject) =>
			setTimeout(() => reject(new Error(`[savedBeanSync] ${label} timed out after ${ms}ms`)), ms)
		)
	]);
}

/**
 * Sync saved beans from server to local database.
 */
export async function syncSavedBeans(options: SavedBeanSyncOptions = {}): Promise<{
	success: boolean;
	error?: string;
	pushed?: number;
	pulledAdded?: number;
	pulledUpdated?: number;
	pulledDeleted?: number;
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

		// Set the current user context for local queries
		setCurrentOwnerId(userId);

		// Claim any unowned (guest) saved beans for this user
		await claimUnownedSavedBeans(userId);

		console.log(`[savedBeanSync] Starting saved beans sync for user ${userId}...`);

		// 1. Push local changes
		const pushedCount = await pushLocalChanges(userId);

		// 2. Pull & reconcile remote changes
		const pullResult = await pullAndReconcile(userId);

		console.log('[savedBeanSync] Saved beans sync completed successfully');
		return {
			success: true,
			pushed: pushedCount,
			pulledAdded: pullResult.added,
			pulledUpdated: pullResult.updated,
			pulledDeleted: pullResult.deleted
		};
	} catch (error) {
		console.error('[savedBeanSync] Saved beans sync failed:', error);
		return { success: false, error: String(error) };
	} finally {
		isSyncing = false;
	}
}

/**
 * Find records modified locally since last sync and push them to server.
 */
async function pushLocalChanges(userId: string): Promise<number> {
	console.log('[savedBeanSync] Checking for local changes to push...');

	// Get all unsynced or soft-deleted records for this user
	const localDirty = await withTimeout(
		db.savedBeans
			.filter(b => (!b.syncedAt || (b.updatedAt || 0) > (b.syncedAt || 0) || b.deletedAt !== null) && (b.ownerId === userId || !b.ownerId))
			.toArray(),
		5000,
		'push:read'
	);

	if (localDirty.length === 0) {
		console.log('[savedBeanSync] No local saved bean changes to push');
		return 0;
	}

	console.log(`[savedBeanSync] Pushing ${localDirty.length} local saved bean changes...`);
	let pushedCount = 0;

	for (const local of localDirty) {
		try {
			if (local.deletedAt !== null) {
				// Only call remote unsave if the bean was actually synced to the server
				if (local.syncedAt) {
					console.log(`[savedBeanSync] Pushing soft-deleted saved bean ${local.syncId}...`);
					await unsaveBean({ savedBeanId: local.syncId });
				}
				await db.savedBeans.delete(local.id!);
				pushedCount++;
			} else if (!local.syncedAt) {
				console.log(`[savedBeanSync] Pushing newly saved bean ${local.beanUrlPath}...`);
				const response = await saveBean({
					beanUrlPath: local.beanUrlPath,
					notes: local.notes || ''
				});
				if (response?.id) {
					await db.savedBeans.update(local.id!, {
						syncId: response.id,
						syncedAt: Date.now(),
						ownerId: userId
					});
					pushedCount++;
				}
			} else if ((local.updatedAt || 0) > (local.syncedAt || 0)) {
				console.log(`[savedBeanSync] Pushing updated notes for saved bean ${local.syncId}...`);
				await updateBeanNotes({
					savedBeanId: local.syncId,
					notes: local.notes || ''
				});
				await db.savedBeans.update(local.id!, {
					syncedAt: Date.now(),
					ownerId: userId
				});
				pushedCount++;
			}
		} catch (error: any) {
			if (error instanceof TypeError || error.name === 'TypeError' || String(error).includes('fetch')) {
				console.warn(`[savedBeanSync] Network error pushing bean ${local.syncId}, will retry later.`);
			} else {
				console.error(`[savedBeanSync] Error pushing saved bean ${local.syncId}:`, error);
			}
		}
	}

	if (pushedCount > 0) {
		notifyUpdate('savedBeans');
	}
	return pushedCount;
}

/**
 * Fetch all remote saved beans and perform complete reconciliation.
 *
 * P4 fix: only delete local records that the server once acknowledged
 * (`syncedAt` is set) and that are missing from the remote list. Records that
 * were never pushed (`!syncedAt`) are un-pushed guest edits that need to be
 * pushed, not deleted.
 */
async function pullAndReconcile(userId: string): Promise<{ added: number; updated: number; deleted: number }> {
	console.log('[savedBeanSync] Pulling remote saved beans list for full reconciliation...');

	const remoteBeans = await getSavedBeans();
	console.log(`[savedBeanSync] Pulled ${remoteBeans.length} remote saved beans`);

	const localBeans = await withTimeout(
		db.savedBeans
			.filter(b => b.ownerId === userId || !b.ownerId)
			.toArray(),
		5000,
		'reconcile:read'
	);

	const localBySyncId = new Map(localBeans.map(b => [b.syncId, b]));
	const remoteBySyncId = new Map(remoteBeans.map(b => [b.id, b]));

	const toDeleteIds: number[] = [];
	const toAdd: LocalSavedBean[] = [];
	const toPut: LocalSavedBean[] = [];

	const beansToFetch = new Set<string>();

	// 1. Reconcile deletions (only for records the server once acknowledged).
	for (const local of localBeans) {
		// Skip locally soft-deleted records (they were processed in push)
		if (local.deletedAt !== null) continue;

		// Skip un-pushed local records — they need to be pushed, not deleted.
		if (!local.syncedAt) continue;

		if (!remoteBySyncId.has(local.syncId)) {
			console.log(`[savedBeanSync] Synced local record ${local.syncId} (path: ${local.beanUrlPath}) missing on server - deleting locally.`);
			toDeleteIds.push(local.id!);
		}
	}

	// 2. Reconcile additions and updates
	for (const remote of remoteBeans) {
		const local = localBySyncId.get(remote.id);
		const remoteUpdatedAt = new Date(remote.updatedAt).getTime();
		const remoteCreatedAt = new Date(remote.createdAt).getTime();

		if (!local) {
			console.log(`[savedBeanSync] Remote record missing locally: adding ${remote.id} (${remote.beanUrlPath})`);
			toAdd.push({
				syncId: remote.id,
				beanUrlPath: remote.beanUrlPath,
				notes: remote.notes,
				createdAt: remoteCreatedAt,
				updatedAt: remoteUpdatedAt,
				deletedAt: null,
				syncedAt: Date.now(),
				ownerId: userId
			});
			beansToFetch.add(remote.beanUrlPath);
		} else if (remoteUpdatedAt > (local.updatedAt || 0)) {
			console.log(`[savedBeanSync] Remote is newer for ${remote.id}. Updating local.`);
			toPut.push({
				...local,
				notes: remote.notes,
				updatedAt: remoteUpdatedAt,
				syncedAt: Date.now()
			});
			if (!local.beanData) {
				beansToFetch.add(remote.beanUrlPath);
			}
		}
	}

	// 3. Batch rehydrate public bean data (prices, stock, tasting notes, etc.)
	//    via paginated helper to avoid silent truncation when >20 unique paths.
	const beanCache = new Map<string, CoffeeBean>();
	if (beansToFetch.size > 0) {
		console.log(`[savedBeanSync] Rehydrating ${beansToFetch.size} unique beans/paths...`);

		// Check local custom beans mirror first
		const localCustomBeans = await db.customBeans
			.filter(b => beansToFetch.has(b.beanUrlPath))
			.toArray();

		for (const b of localCustomBeans) {
			beanCache.set(b.beanUrlPath, b.beanData);
			beansToFetch.delete(b.beanUrlPath);
		}

		// Then fetch remaining from public API
		if (beansToFetch.size > 0) {
			try {
				const beans = await api.fetchAllBeansByPaths(Array.from(beansToFetch));
				for (const bean of beans) {
					if (bean.bean_url_path) beanCache.set(bean.bean_url_path, bean);
				}
			} catch (error) {
				console.error('[savedBeanSync] Failed to rehydrate beans during saved bean sync:', error);
			}
		}
	}

	// Attach rehydrated beanData to added items
	for (const data of toAdd) {
		const cached = beanCache.get(data.beanUrlPath);
		if (cached) {
			data.beanData = cached;
		}
	}

	// Attach rehydrated beanData to updated items if they didn't have it
	for (const data of toPut) {
		if (!data.beanData) {
			const cached = beanCache.get(data.beanUrlPath);
			if (cached) {
				data.beanData = cached;
			}
		}
	}

	// 4. Perform atomic batch updates
	if (toDeleteIds.length > 0) {
		await db.savedBeans.bulkDelete(toDeleteIds);
	}
	if (toAdd.length > 0) {
		await db.savedBeans.bulkAdd(toAdd);
	}
	if (toPut.length > 0) {
		await db.savedBeans.bulkPut(toPut);
	}

	if (toDeleteIds.length > 0 || toAdd.length > 0 || toPut.length > 0) {
		notifyUpdate('savedBeans');
	}

	return {
		added: toAdd.length,
		updated: toPut.length,
		deleted: toDeleteIds.length
	};
}
