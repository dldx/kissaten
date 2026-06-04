import { db, type TastingSession, setCurrentOwnerId, claimUnownedTastings } from '$lib/db/localdb';
import { pushTastings, pullTastings } from '$lib/api/tastings.remote';
import { getUserWithoutRedirect } from '$lib/api/auth.remote';

function getLastSyncKey(userId: string): string {
	return `kissaten_last_tasting_sync_${userId}`;
}

/**
 * Main sync function: pushes local changes then pulls remote changes
 * Scoped to the currently authenticated user.
 */
export async function syncTastings(): Promise<{ success: boolean; error?: string }> {
	try {
		const user = await getUserWithoutRedirect();
		if (!user) {
			console.log('Skipping sync: user not authenticated');
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
			await pushLocalChanges(userId);
		} catch (error) {
			console.error('Failed to push local changes:', error);
			// Continue to pull even if push fails
		}

		// 2. Pull remote changes
		try {
			await pullRemoteChanges(userId);
		} catch (error) {
			console.error('Failed to pull remote changes:', error);
			throw error; // Re-throw to catch in main try-block
		}

		console.log('Tasting sync completed successfully');
		return { success: true };
	} catch (error) {
		console.error('Tasting sync failed:', error);
		return { success: false, error: String(error) };
	}
}

/**
 * Find records modified locally since last sync and push them to server.
 * Only pushes records belonging to the specified user.
 */
async function pushLocalChanges(userId: string) {
	// Find all dirty records belonging to this user
	const dirtyRecords = await db.tastings
		.where('ownerId')
		.equals(userId)
		.filter(t => !t.syncedAt || (t.updatedAt || 0) > t.syncedAt)
		.toArray();

	if (dirtyRecords.length === 0) {
		console.log('No local changes to push');
		return;
	}

	console.log(`Pushing ${dirtyRecords.length} dirty records to server...`);

	const syncPayload = dirtyRecords.map(r => ({
		id: r.syncId!,
		data: JSON.stringify(r),
		updatedAt: r.updatedAt!,
		deletedAt: r.deletedAt || null
	}));

	const result = await pushTastings(syncPayload);

	if (result.success) {
		// Update syncedAt timestamp locally
		const now = Date.now();
		await db.transaction('rw', db.tastings, async () => {
			for (const record of dirtyRecords) {
				await db.tastings.update(record.id!, { syncedAt: now });
			}
		});
		console.log('Successfully pushed local changes');
	}
}

/**
 * Fetch records modified on server since last sync and merge them locally.
 * Uses a per-user sync cursor so switching accounts doesn't corrupt the timeline.
 */
async function pullRemoteChanges(userId: string) {
	const lastSyncKey = getLastSyncKey(userId);
	const lastSync = Number(localStorage.getItem(lastSyncKey) || '0');

	console.log(`Pulling remote changes since ${new Date(lastSync).toISOString()}...`);

	const remoteRecords = await pullTastings(lastSync);

	if (remoteRecords.length === 0) {
		console.log('No remote changes to pull');
		return;
	}

	console.log(`Pulled ${remoteRecords.length} remote records`);

	await db.transaction('rw', db.tastings, async () => {
		for (const remote of remoteRecords) {
			const local = await db.tastings.where('syncId').equals(remote.id).first();

			// If remote is deleted
			if (remote.deletedAt) {
				if (local) {
					console.log(`Deleting local record ${remote.id} (remote delete)`);
					await db.tastings.delete(local.id!);
				}
				continue;
			}

			const remoteData = JSON.parse(remote.data) as TastingSession;

			// Log for debugging RangeError
			console.log(`Processing remote record ${remote.id}, raw date:`, remoteData.date);

			// Ensure date is a proper Date object for Dexie
			if (remoteData.date && typeof remoteData.date === 'string') {
				console.log(`Converting string date ${remoteData.date} to Date object`);
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
			remoteData.ownerId = userId; // Tag with the current user

			if (!local) {
				// New record from remote
				console.log(`Adding new remote record ${remote.id}`);
				await db.tastings.add(remoteData);
			} else if (remote.updatedAt > (local.updatedAt || 0)) {
				// Remote is newer, update local
				console.log(`Updating local record ${remote.id} with newer remote data`);
				// Preserve local ID
				await db.tastings.put({ ...remoteData, id: local.id });
			} else {
				console.log(`Skipping remote record ${remote.id} (local is same or newer)`);
			}
		}
	});

	// 3. Update last sync timestamp only after a successful complete sync cycle
	localStorage.setItem(lastSyncKey, Date.now().toString());
	console.log('Successfully pulled and merged remote changes');
}
