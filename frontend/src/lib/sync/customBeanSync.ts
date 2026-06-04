import { db, type LocalCustomBean } from '$lib/db/localdb';
import { pushCustomBeans, pullCustomBeans } from '$lib/api/custom_beans.remote';
import { getUserWithoutRedirect } from '$lib/api/auth.remote';
import { type CoffeeBean } from '$lib/api';
import { notifyUpdate } from '$lib/db/updates.svelte';

function getLastSyncKey(userId: string): string {
    return `kissaten_last_custom_bean_sync_${userId}`;
}

export async function syncCustomBeans(): Promise<void> {
    const user = await getUserWithoutRedirect();
    if (!user) return;

    try {
        console.log('Starting custom bean sync...');
        await pushLocalCustomBeanChanges(user.id);
        await pullRemoteCustomBeanChanges(user.id);
        console.log('Custom bean sync completed successfully');
    } catch (error) {
        console.error('Custom bean sync failed:', error);
    }
}

async function pushLocalCustomBeanChanges(userId: string): Promise<void> {
    const localRecords = await db.customBeans
        .filter(b => (!b.syncedAt || b.updatedAt > b.syncedAt) && (b.ownerId === userId || !b.ownerId))
        .toArray();

    if (localRecords.length === 0) {
        console.log('No local custom bean changes to push');
        return;
    }

    const BATCH_SIZE = 50;
    for (let i = 0; i < localRecords.length; i += BATCH_SIZE) {
        const batch = localRecords.slice(i, i + BATCH_SIZE);
        const syncPayload = batch.map(b => ({
            id: b.syncId,
            beanData: JSON.stringify(b.beanData),
            updatedAt: b.updatedAt,
            deletedAt: b.deletedAt
        }));

        await pushCustomBeans(syncPayload);

        // Update syncedAt
        await db.transaction('rw', db.customBeans, async () => {
            for (const record of batch) {
                await db.customBeans.update(record.id!, {
                    syncedAt: Date.now(),
                    ownerId: userId
                });
            }
        });
    }
}

async function pullRemoteCustomBeanChanges(userId: string): Promise<void> {
    const lastSyncKey = getLastSyncKey(userId);
    const lastSync = parseInt(localStorage.getItem(lastSyncKey) || '0');

    console.log(`Pulling remote custom beans since ${new Date(lastSync).toISOString()}...`);
    const remoteRecords = await pullCustomBeans(lastSync);

    if (remoteRecords.length === 0) {
        console.log('No remote custom bean changes to pull');
        localStorage.setItem(lastSyncKey, Date.now().toString());
        return;
    }

    await db.transaction('rw', db.customBeans, async () => {
        for (const remote of remoteRecords) {
            const local = await db.customBeans.where('syncId').equals(remote.id).first();
            const beanData = JSON.parse(remote.data) as CoffeeBean;

            if (remote.deletedAt) {
                if (local) {
                    await db.customBeans.delete(local.id!);
                }
                continue;
            }

            if (!local) {
                await db.customBeans.add({
                    syncId: remote.id,
                    beanUrlPath: beanData.bean_url_path!,
                    beanData: beanData,
                    updatedAt: remote.updatedAt,
                    deletedAt: null,
                    syncedAt: Date.now(),
                    ownerId: userId
                });
            } else if (remote.updatedAt > local.updatedAt) {
                await db.customBeans.update(local.id!, {
                    beanData: beanData,
                    beanUrlPath: beanData.bean_url_path!,
                    updatedAt: remote.updatedAt,
                    syncedAt: Date.now(),
                    ownerId: userId
                });
            }
        }
    });

    localStorage.setItem(lastSyncKey, Date.now().toString());
    notifyUpdate('customBeans');
}
