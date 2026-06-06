import { toast } from 'svelte-sonner';
import { syncTastings } from './tastingSync';
import { syncCustomBeans } from './customBeanSync';
import { syncSavedBeans } from './savedBeanSync';

export const syncState = (() => {
	let isSyncing = $state(false);
	let lastSyncTime = $state<number | null>(null);

	return {
		get isSyncing() {
			return isSyncing;
		},
		get lastSyncTime() {
			return lastSyncTime;
		},
		setSyncing(value: boolean) {
			isSyncing = value;
		},
		setLastSyncTime(value: number) {
			lastSyncTime = value;
		}
	};
})();

/**
 * Runs a complete sync of tastings, custom beans, and saved beans.
 *
 * @param options.silent If true, only raises toasts when changes were actually synchronized.
 *                        If false, always raises loading/completed toasts.
 */
export async function runGlobalSync(options: { silent?: boolean } = { silent: true }): Promise<void> {
	if (syncState.isSyncing) {
		console.log('[syncManager] Sync already in progress, skipping...');
		return;
	}

	syncState.setSyncing(true);
	let toastId: string | number | null = null;

	if (typeof navigator !== 'undefined' && !navigator.onLine) {
		console.log('[syncManager] Device is offline, skipping global sync.');
		syncState.setSyncing(false);
		if (!options.silent) {
			toast.error('Cannot sync while offline');
		}
		return;
	}

	if (!options.silent) {
		toastId = toast.loading('Syncing your coffee database...');
	}

	try {
		const [tastingResult, customBeanResult, savedBeanResult] = await Promise.allSettled([
			syncTastings(),
			syncCustomBeans(),
			syncSavedBeans()
		]);

		let tastingAdded = 0;
		let tastingUpdated = 0;
		let tastingDeleted = 0;
		let tastingPushed = 0;
		let tastingsSuccess = false;
		let tastingsAuthError = false;

		if (tastingResult.status === 'fulfilled') {
			const res = tastingResult.value;
			tastingsSuccess = res.success;
			if (res.success) {
				tastingAdded = res.pulledAdded || 0;
				tastingUpdated = res.pulledUpdated || 0;
				tastingDeleted = res.pulledDeleted || 0;
				tastingPushed = res.pushed || 0;
			} else if (res.error === 'Not authenticated') {
				tastingsAuthError = true;
			}
		}

		let customAdded = 0;
		let customUpdated = 0;
		let customDeleted = 0;
		let customPushed = 0;
		let customSuccess = false;
		let customAuthError = false;

		if (customBeanResult.status === 'fulfilled') {
			const res = customBeanResult.value;
			customSuccess = res.success;
			if (res.success) {
				customAdded = res.pulledAdded || 0;
				customUpdated = res.pulledUpdated || 0;
				customDeleted = res.pulledDeleted || 0;
				customPushed = res.pushed || 0;
			} else if (res.error === 'Not authenticated') {
				customAuthError = true;
			}
		}

		let savedAdded = 0;
		let savedUpdated = 0;
		let savedSuccess = false;
		let savedAuthError = false;

		if (savedBeanResult.status === 'fulfilled') {
			const res = savedBeanResult.value;
			savedSuccess = res.success;
			if (res.success) {
				savedAdded = res.pulledAdded || 0;
				savedUpdated = res.pulledUpdated || 0;
			} else if (res.error === 'Not authenticated') {
				savedAuthError = true;
			}
		}

		const totalPushed = tastingPushed + customPushed;
		const totalAdded = tastingAdded + customAdded + savedAdded;
		const totalUpdated = tastingUpdated + customUpdated + savedUpdated;
		const totalDeleted = tastingDeleted + customDeleted;
		const totalChanges = totalPushed + totalAdded + totalUpdated + totalDeleted;

		const isAuthErrorOnly = tastingsAuthError && customAuthError && savedAuthError;
		const anyFailed = !tastingsSuccess || !customSuccess || !savedSuccess;

		// Build a human-readable summary of what changed, e.g. "pushed 2, added 1"
		const summaryParts: string[] = [];
		if (totalPushed > 0) summaryParts.push(`pushed ${totalPushed}`);
		if (totalAdded > 0) summaryParts.push(`added ${totalAdded}`);
		if (totalUpdated > 0) summaryParts.push(`updated ${totalUpdated}`);
		if (totalDeleted > 0) summaryParts.push(`deleted ${totalDeleted}`);
		const summary = summaryParts.join(', ');

		syncState.setLastSyncTime(Date.now());

		if (toastId !== null) {
			// Explicit manual sync
			if (anyFailed && !isAuthErrorOnly) {
				toast.error('Sync completed with some errors', { id: toastId });
			} else if (isAuthErrorOnly) {
				toast.info('Sign in to synchronize your coffee data', { id: toastId });
			} else if (totalChanges > 0) {
				toast.success(`Sync completed: ${summary}`, { id: toastId });
			} else {
				toast.success('Everything is up-to-date!', { id: toastId });
			}
		} else if (totalChanges > 0 && !isAuthErrorOnly) {
			// Silent background sync: only notify when something actually changed
			toast.success(`Sync finished: ${summary}`, {
				description: 'Your local coffee data is now up-to-date.'
			});
		}
	} catch (error) {
		console.error('[syncManager] Global sync execution failed:', error);
		if (toastId !== null) {
			toast.error('Global synchronization failed', { id: toastId });
		}
	} finally {
		syncState.setSyncing(false);
	}
}
