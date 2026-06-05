import { db, type LocalCustomBean } from '$lib/db/localdb';
import { pushCustomBeans, pullCustomBeans } from '$lib/api/custom_beans.remote';
import { getUserWithoutRedirect } from '$lib/api/auth.remote';
import { type CoffeeBean } from '$lib/api';
import { notifyUpdate } from '$lib/db/updates.svelte';

function getLastSyncKey(userId: string): string {
    return `kissaten_last_custom_bean_sync_${userId}`;
}

/** Race a promise against a timeout. Rejects if the promise doesn't resolve in time. */
function withTimeout<T>(promise: Promise<T>, ms: number, label: string): Promise<T> {
    return Promise.race([
        promise,
        new Promise<never>((_, reject) =>
            setTimeout(() => reject(new Error(`[customBeanSync] ${label} timed out after ${ms}ms`)), ms)
        )
    ]);
}

let isSyncing = false;

/** Exposed for diagnostic reads from AddBeanForm and other components */
export function isCustomBeanSyncActive(): boolean {
    return isSyncing;
}

export async function syncCustomBeans(): Promise<{
    success: boolean;
    error?: string;
    pushed?: number;
    pulledAdded?: number;
    pulledUpdated?: number;
    pulledDeleted?: number;
}> {
    if (isSyncing) {
        console.log('[customBeanSync] Sync already in progress, skipping...');
        return { success: false, error: 'Sync already in progress' };
    }

    // Set syncing flag immediately to block concurrent invocations while we resolve the user session
    isSyncing = true;
    let pushedCount = 0;

    try {
        const user = await getUserWithoutRedirect();
        if (!user) {
            isSyncing = false;
            return { success: false, error: 'Not authenticated' };
        }

        console.log('[customBeanSync] Starting custom bean sync...');
        try {
            pushedCount = await pushLocalCustomBeanChanges(user.id);
        } catch (error) {
            console.error('[customBeanSync] Failed to push local custom bean changes:', error);
        }

        let pullResult = { added: 0, updated: 0, deleted: 0 };
        try {
            pullResult = await pullRemoteCustomBeanChanges(user.id);
        } catch (error) {
            console.error('[customBeanSync] Failed to pull remote custom bean changes:', error);
            throw error;
        }

        console.log('[customBeanSync] Custom bean sync completed successfully');
        return {
            success: true,
            pushed: pushedCount,
            pulledAdded: pullResult.added,
            pulledUpdated: pullResult.updated,
            pulledDeleted: pullResult.deleted
        };
    } catch (error) {
        console.error('[customBeanSync] Custom bean sync failed:', error);
        return { success: false, error: String(error) };
    } finally {
        isSyncing = false;
    }
}

async function pushLocalCustomBeanChanges(userId: string): Promise<number> {
    console.log('[customBeanSync] pushLocalCustomBeanChanges: reading dirty records...');
    const localRecords = await withTimeout(
        db.customBeans
            .filter(b => (!b.syncedAt || b.updatedAt > b.syncedAt) && (b.ownerId === userId || !b.ownerId))
            .toArray(),
        5000,
        'push:read'
    );

    if (localRecords.length === 0) {
        console.log('[customBeanSync] No local custom bean changes to push');
        return 0;
    }

    console.log(`[customBeanSync] Pushing ${localRecords.length} local custom bean changes...`);
    const BATCH_SIZE = 50;
    for (let i = 0; i < localRecords.length; i += BATCH_SIZE) {
        const batch = localRecords.slice(i, i + BATCH_SIZE);
        const syncPayload = batch.map(b => ({
            id: b.syncId,
            beanData: JSON.stringify(b.beanData),
            updatedAt: b.updatedAt,
            deletedAt: b.deletedAt
        }));

        console.log('[customBeanSync] push: sending network request...');
        await pushCustomBeans(syncPayload);

        // Update syncedAt using non-blocking bulkPut with timeout protection
        const now = Date.now();
        const updated = batch.map(record => ({
            ...record,
            syncedAt: now,
            ownerId: userId
        }));
        console.log('[customBeanSync] push: writing bulkPut...');
        await withTimeout(db.customBeans.bulkPut(updated), 5000, 'push:bulkPut');
        console.log(`[customBeanSync] Push batch ${Math.floor(i / BATCH_SIZE) + 1} synced`);
    }
    return localRecords.length;
}

async function pullRemoteCustomBeanChanges(userId: string): Promise<{ added: number; updated: number; deleted: number }> {
    const lastSyncKey = getLastSyncKey(userId);
    const lastSync = parseInt(localStorage.getItem(lastSyncKey) || '0');

    console.log(`[customBeanSync] Pulling remote custom beans since ${new Date(lastSync).toISOString()}...`);
    const remoteRecords = await pullCustomBeans(lastSync);

    if (remoteRecords.length === 0) {
        console.log('[customBeanSync] No remote custom bean changes to pull');
        localStorage.setItem(lastSyncKey, Date.now().toString());
        return { added: 0, updated: 0, deleted: 0 };
    }

    console.log(`[customBeanSync] Processing ${remoteRecords.length} remote custom bean records...`);

    // Read all local records upfront with timeout protection
    console.log('[customBeanSync] pull: reading all local customBeans...');
    const allLocal = await withTimeout(db.customBeans.toArray(), 5000, 'pull:toArray');
    console.log(`[customBeanSync] pull: read ${allLocal.length} local records`);
    const localBySyncId = new Map(allLocal.map(b => [b.syncId, b]));

    const toAdd: any[] = [];
    const toUpdate: any[] = [];
    const toDelete: number[] = [];

    for (const remote of remoteRecords) {
        const local = localBySyncId.get(remote.id);
        const beanData = JSON.parse(remote.data) as CoffeeBean;

        if (remote.deletedAt) {
            if (local) {
                toDelete.push(local.id!);
            }
            continue;
        }

        if (!local) {
            toAdd.push({
                syncId: remote.id,
                beanUrlPath: beanData.bean_url_path!,
                beanData: beanData,
                updatedAt: remote.updatedAt,
                deletedAt: null,
                syncedAt: Date.now(),
                ownerId: userId
            });
        } else if (remote.updatedAt > local.updatedAt) {
            toUpdate.push({
                ...local,
                beanData: beanData,
                beanUrlPath: beanData.bean_url_path!,
                updatedAt: remote.updatedAt,
                syncedAt: Date.now(),
                ownerId: userId
            });
        }
    }

    // Execute writes with timeout protection to prevent permanent store locking
    // Deep clone records to strip Svelte reactive proxy descriptors, ensuring safe Structured Cloning inside IndexedDB
    if (toDelete.length > 0) {
        console.log(`[customBeanSync] pull: bulkDelete ${toDelete.length} records...`);
        const cleanToDelete = JSON.parse(JSON.stringify(toDelete));
        await withTimeout(db.customBeans.bulkDelete(cleanToDelete), 5000, 'pull:bulkDelete');
        console.log(`[customBeanSync] Deleted ${toDelete.length} remote-deleted beans`);
    }
    if (toAdd.length > 0) {
        console.log(`[customBeanSync] pull: bulkAdd ${toAdd.length} records...`);
        const cleanToAdd = JSON.parse(JSON.stringify(toAdd));
        await withTimeout(db.customBeans.bulkAdd(cleanToAdd), 5000, 'pull:bulkAdd');
        console.log(`[customBeanSync] Added ${toAdd.length} new remote beans`);
    }
    if (toUpdate.length > 0) {
        console.log(`[customBeanSync] pull: bulkPut ${toUpdate.length} records...`);
        const cleanToUpdate = JSON.parse(JSON.stringify(toUpdate));
        await withTimeout(db.customBeans.bulkPut(cleanToUpdate), 5000, 'pull:bulkPut');
        console.log(`[customBeanSync] Updated ${toUpdate.length} existing beans`);
    }

    localStorage.setItem(lastSyncKey, Date.now().toString());
    notifyUpdate('customBeans');

    return {
        added: toAdd.length,
        updated: toUpdate.length,
        deleted: toDelete.length
    };
}
