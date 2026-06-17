import { db, type LocalBrewRecipe, setCurrentOwnerId, claimUnownedBrewRecipes } from '$lib/db/localdb';
import { pushBrewRecipes, pullBrewRecipes } from '$lib/api/brew.remote';
import { getUserWithoutRedirect } from '$lib/api/auth.remote';
import { notifyUpdate } from '$lib/db/updates.svelte';

export type BrewRecipeSyncOptions = {
	/** When true, reset the `since` cursor before pulling so we re-fetch every
	 *  saved brew recipe the user owns. Used by verification-triggered repair
	 *  runs. */
	forceFullSync?: boolean;
};

function getLastSyncKey(userId: string): string {
	return `kissaten_last_recipe_sync_${userId}`;
}

function clearLastSyncKey(userId: string): void {
	if (typeof localStorage === 'undefined') return;
	localStorage.removeItem(getLastSyncKey(userId));
}

let isSyncing = false;

/**
 * Main sync function: pushes local changes then pulls remote changes
 * Scoped to the currently authenticated user.
 */
export async function syncBrewRecipes(options: BrewRecipeSyncOptions = {}): Promise<{
	success: boolean;
	error?: string;
	pushed?: number;
	pulledAdded?: number;
	pulledUpdated?: number;
	pulledDeleted?: number;
}> {
	if (isSyncing) {
		console.log('[brewRecipeSync] Sync already in progress, skipping...');
		return { success: false, error: 'Sync already in progress' };
	}

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
		setCurrentOwnerId(userId);

		// Claim any unowned (guest) brew recipes for this user
		await claimUnownedBrewRecipes(userId);

		console.log(`Starting brew recipe sync for user ${userId}${options.forceFullSync ? ' (force-full)' : ''}...`);

		// 1. Push local changes
		try {
			pushedCount = await pushLocalChanges(userId);
		} catch (error: any) {
			console.error('Failed to push local changes:', error);
		}

		// 2. Pull remote changes
		let pullResult = { added: 0, updated: 0, deleted: 0 };
		try {
			pullResult = await pullRemoteChanges(userId, options.forceFullSync ?? false);
		} catch (error: any) {
			console.error('Failed to pull remote changes:', error);
			throw error;
		}

		console.log('Brew recipe sync completed successfully');
		return {
			success: true,
			pushed: pushedCount,
			pulledAdded: pullResult.added,
			pulledUpdated: pullResult.updated,
			pulledDeleted: pullResult.deleted
		};
	} catch (error) {
		console.error('Brew recipe sync failed:', error);
		return { success: false, error: String(error) };
	} finally {
		isSyncing = false;
	}
}

async function pushLocalChanges(userId: string): Promise<number> {
	// Find all dirty records belonging to this user that are marked as saved
	const dirtyRecords = await db.brewRecipes
		.where('ownerId')
		.equals(userId)
		.filter(r => r.isSaved && (!r.syncedAt || (r.updatedAt || 0) > r.syncedAt))
		.toArray();

	if (dirtyRecords.length === 0) {
		console.log('No local changes to push');
		return 0;
	}

	console.log(`Pushing ${dirtyRecords.length} dirty recipes to server...`);

	const syncPayload = dirtyRecords.map(r => {
		const { id, ...data } = r;
		return {
			id: r.syncId!,
			data: JSON.stringify(data),
			updatedAt: r.updatedAt!,
			deletedAt: r.deletedAt || null
		};
	});

	const BATCH_SIZE = 5;
	for (let i = 0; i < syncPayload.length; i += BATCH_SIZE) {
		const batch = syncPayload.slice(i, i + BATCH_SIZE);
		const result = await pushBrewRecipes(batch);

		if (result.success) {
			const now = Date.now();
			const batchRecords = dirtyRecords.slice(i, i + BATCH_SIZE);
			const updated = batchRecords.map(record => ({ ...record, syncedAt: now }));
			await db.brewRecipes.bulkPut(updated);
		} else {
			break;
		}
	}

	return dirtyRecords.length;
}

async function pullRemoteChanges(userId: string, forceFullSync: boolean): Promise<{ added: number; updated: number; deleted: number }> {
	const lastSyncKey = getLastSyncKey(userId);
	const lastSync = forceFullSync ? 0 : Number(localStorage.getItem(lastSyncKey) || '0');

	if (forceFullSync) {
		console.log('[brewRecipeSync] Force-full pull: clearing cursor and re-fetching everything.');
		clearLastSyncKey(userId);
	}

	const remoteRecords = await pullBrewRecipes(lastSync);

	if (remoteRecords.length === 0) {
		if (!forceFullSync) {
			localStorage.setItem(lastSyncKey, Date.now().toString());
		}
		return { added: 0, updated: 0, deleted: 0 };
	}

	const localBySyncId = new Map(
		(await db.brewRecipes.where('syncId').anyOf(remoteRecords.map(r => r.id)).toArray())
			.map(t => [t.syncId!, t])
	);

	const toAdd: LocalBrewRecipe[] = [];
	const toPut: LocalBrewRecipe[] = [];
	const toDeleteIds: number[] = [];

	for (const remote of remoteRecords) {
		const data = JSON.parse(remote.data) as LocalBrewRecipe;
		delete (data as any).id;

		const local = localBySyncId.get(remote.id);

		if (remote.deletedAt) {
			if (local) toDeleteIds.push(local.id!);
			continue;
		}

		data.syncId = remote.id;
		data.updatedAt = remote.updatedAt;
		data.syncedAt = Date.now();
		data.ownerId = userId;

		if (!local) {
			toAdd.push(data);
		} else if (remote.updatedAt > (local.updatedAt || 0)) {
			toPut.push({ ...data, id: local.id });
		}
	}

	if (toDeleteIds.length > 0) await db.brewRecipes.bulkDelete(toDeleteIds);
	if (toAdd.length > 0) await db.brewRecipes.bulkAdd(toAdd);
	if (toPut.length > 0) await db.brewRecipes.bulkPut(toPut);

	localStorage.setItem(lastSyncKey, Date.now().toString());
	notifyUpdate('brewRecipes' as any);

	return {
		added: toAdd.length,
		updated: toPut.length,
		deleted: toDeleteIds.length
	};
}
