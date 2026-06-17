import { toast } from 'svelte-sonner';
import { syncTastings } from './tastingSync';
import { syncCustomBeans } from './customBeanSync';
import { syncSavedBeans } from './savedBeanSync';
import { syncBrewRecipes } from './brewRecipeSync';
import { verifySyncConsistency, type SyncType } from './verifySync';

export type SyncMode = 'normal' | 'verify-then-fix' | 'force-full';

export type RunGlobalSyncOptions = {
	/** Whether to suppress info toasts and only toast on changes/errors.
	 *  Default `true` (silent background sync). */
	silent?: boolean;
	/** Sync strategy:
	 *  - 'normal' (default): incremental push+pull for all four tables.
	 *  - 'verify-then-fix': run `verifySyncConsistency`; if any drift is found,
	 *    force-full sync the affected tables silently.
	 *  - 'force-full': unconditionally force-full sync all four tables. */
	mode?: SyncMode;
};

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
 * Runs a complete sync of tastings, custom beans, saved beans, and brew recipes.
 *
 * - `mode: 'normal'` (default) — incremental sync using the existing `since` cursors.
 * - `mode: 'verify-then-fix'` — run a count+digest consistency check; if any table
 *   drifts, force-full sync that table silently and surface a toast only on change.
 * - `mode: 'force-full'` — unconditionally ignore cursors and re-fetch everything.
 *
 * When `silent` is true (default), toasts fire only when changes were made.
 * When `silent` is false, a loading toast is shown and replaced with a summary.
 */
export async function runGlobalSync(options: RunGlobalSyncOptions = {}): Promise<void> {
	const silent = options.silent ?? true;
	const mode = options.mode ?? 'normal';

	if (syncState.isSyncing) {
		console.log('[syncManager] Sync already in progress, skipping...');
		return;
	}

	syncState.setSyncing(true);
	let toastId: string | number | null = null;

	if (typeof navigator !== 'undefined' && !navigator.onLine) {
		console.log('[syncManager] Device is offline, skipping global sync.');
		syncState.setSyncing(false);
		if (!silent) {
			toast.error('Cannot sync while offline');
		}
		return;
	}

	if (!silent) {
		toastId = toast.loading(
			mode === 'force-full'
				? 'Performing a full sync of your coffee database...'
				: mode === 'verify-then-fix'
					? 'Checking your sync consistency...'
					: 'Syncing your coffee database...'
		);
	}

	try {
		// Resolve which tables need force-full sync.
		const forceFor = new Set<SyncType>();
		if (mode === 'force-full') {
			forceFor.add('tastings');
			forceFor.add('customBeans');
			forceFor.add('savedBeans');
			forceFor.add('brewRecipes');
		} else if (mode === 'verify-then-fix') {
			try {
				const verification = await verifySyncConsistency();
				if (!verification.ok) {
					for (const issue of verification.issues) {
						forceFor.add(issue.type);
					}
					console.log(
						`[syncManager] verifySyncConsistency found drift in: ${[...forceFor].join(', ') || 'none'}`
					);
				} else {
					console.log('[syncManager] verifySyncConsistency: all tables consistent.');
				}
			} catch (error) {
				console.warn('[syncManager] Verification failed, falling back to normal sync:', error);
			}
		}

		// If nothing drifted, do a normal sync (no force) so we still get
		// incremental push/pull behavior. The verification itself was cheap.
		const useForce = (type: SyncType) => forceFor.has(type);

		const [tastingResult, customBeanResult, savedBeanResult, brewRecipeResult] = await Promise.allSettled([
			syncTastings({ forceFullSync: useForce('tastings') }),
			syncCustomBeans({ forceFullSync: useForce('customBeans') }),
			syncSavedBeans({ forceFullSync: useForce('savedBeans') }),
			syncBrewRecipes({ forceFullSync: useForce('brewRecipes') })
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

		let recipeAdded = 0;
		let recipeUpdated = 0;
		let recipeDeleted = 0;
		let recipePushed = 0;
		let recipesSuccess = false;
		let recipesAuthError = false;

		if (brewRecipeResult.status === 'fulfilled') {
			const res = brewRecipeResult.value;
			recipesSuccess = res.success;
			if (res.success) {
				recipeAdded = res.pulledAdded || 0;
				recipeUpdated = res.pulledUpdated || 0;
				recipeDeleted = res.pulledDeleted || 0;
				recipePushed = res.pushed || 0;
			} else if (res.error === 'Not authenticated') {
				recipesAuthError = true;
			}
		}

		const totalPushed = tastingPushed + customPushed + recipePushed;
		const totalAdded = tastingAdded + customAdded + savedAdded + recipeAdded;
		const totalUpdated = tastingUpdated + customUpdated + savedUpdated + recipeUpdated;
		const totalDeleted = tastingDeleted + customDeleted + recipeDeleted;
		const totalChanges = totalPushed + totalAdded + totalUpdated + totalDeleted;

		const isAuthErrorOnly = tastingsAuthError && customAuthError && savedAuthError && recipesAuthError;
		const anyFailed = !tastingsSuccess || !customSuccess || !savedSuccess || !recipesSuccess;

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
			const repaired = forceFor.size > 0;
			const prefix = repaired ? 'Sync repaired' : 'Sync finished';
			toast.success(`${prefix}: ${summary}`, {
				description: repaired
					? 'Detected inconsistencies and re-synced affected data.'
					: 'Your local coffee data is now up-to-date.'
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
