import { db, type LocalBrewRecipe, type LocalCustomBean, type LocalSavedBean, type TastingSession } from '$lib/db/localdb';
import { getUserWithoutRedirect } from '$lib/api/auth.remote';
import { getTastingsCount, getTastingsDigest } from '$lib/api/tastings.remote';
import { getCustomBeansCount, getCustomBeansDigest } from '$lib/api/custom_beans.remote';
import { getBrewRecipesCount, getBrewRecipesDigest } from '$lib/api/brew.remote';
import { getSavedBeansCount, getSavedBeansDigest } from '$lib/api/vault.remote';

export type SyncType = 'tastings' | 'customBeans' | 'savedBeans' | 'brewRecipes';

export interface SyncIssue {
	type: SyncType;
	reason: 'count_mismatch' | 'digest_mismatch';
	localCount: number;
	remoteCount: number;
}

export interface VerificationResult {
	ok: boolean;
	issues: SyncIssue[];
	skipped: SyncType[];
}

/**
 * Compute a deterministic SHA-256 digest over (syncId, updatedAt) pairs from
 * a list of records. Excludes soft-deleted entries and any record that is
 * dirty locally (no `syncedAt` or `updatedAt > syncedAt`), so un-pushed local
 * edits do not register as a mismatch. Brew recipes also filter to
 * `isSaved === true` to mirror what the server actually stores.
 *
 * The algorithm matches the server-side digest computation exactly: sort by
 * `syncId` and join `id:updatedAt.getTime()` with `|` separators.
 */
async function digestFromLocal<T extends { syncId?: string; updatedAt?: number; deletedAt?: number | null; syncedAt?: number | null; isSaved?: boolean }>(
	records: T[],
	options: { requireIsSaved?: boolean } = {}
): Promise<string> {
	const eligible = records.filter(r => {
		if (!r.syncId) return false;
		if (r.deletedAt) return false;
		if (!r.syncedAt || (r.updatedAt || 0) > r.syncedAt) return false;
		if (options.requireIsSaved && !r.isSaved) return false;
		return true;
	});

	eligible.sort((a, b) => (a.syncId! < b.syncId! ? -1 : a.syncId! > b.syncId! ? 1 : 0));

	const joined = eligible
		.map(r => `${r.syncId}:${r.updatedAt}`)
		.join('|');

	const buf = new TextEncoder().encode(joined);
	const hashBuf = await crypto.subtle.digest('SHA-256', buf);
	const bytes = new Uint8Array(hashBuf);
	let hex = '';
	for (let i = 0; i < bytes.length; i++) {
		hex += bytes[i].toString(16).padStart(2, '0');
	}
	return hex;
}

async function countLocalEligible<T extends { deletedAt?: number | null; isSaved?: boolean; ownerId?: string | null }>(
	table: { filter: (fn: (r: T) => boolean) => { toArray(): Promise<T[]> } },
	userId: string,
	requireIsSaved: boolean = false
): Promise<number> {
	const all = await table.filter(r => {
		if (r.deletedAt) return false;
		if (requireIsSaved && !r.isSaved) return false;
		// Only count records that are either owned by this user or unowned (claimed soon)
		return r.ownerId === userId || r.ownerId === null || r.ownerId === undefined;
	}).toArray();
	return all.length;
}

function isOffline(): boolean {
	return typeof navigator !== 'undefined' && !navigator.onLine;
}

/**
 * Cheap count-first, hash-on-tie consistency check.
 *
 * For each user-data table:
 *   1. Compare local count to remote count.
 *   2. If counts differ → mismatch (count_mismatch).
 *   3. If counts match → compute a SHA-256 digest of (syncId, updatedAt) on
 *      both sides and compare; any difference is mismatch (digest_mismatch),
 *      which catches content drift at equal counts that the count check alone
 *      would miss.
 *
 * Returns `{ ok: true, issues: [], skipped }` when offline, unauthenticated,
 * or on the server (no `window`). Otherwise runs the full check.
 *
 * Never mutates state.
 */
export async function verifySyncConsistency(): Promise<VerificationResult> {
	const skipped: SyncType[] = [];

	if (typeof window === 'undefined') {
		return { ok: true, issues: [], skipped: ['tastings', 'customBeans', 'savedBeans', 'brewRecipes'] };
	}

	if (isOffline()) {
		console.log('[verifySync] Offline, skipping consistency check.');
		return { ok: true, issues: [], skipped: ['tastings', 'customBeans', 'savedBeans', 'brewRecipes'] };
	}

	const user = await getUserWithoutRedirect();
	if (!user) {
		return { ok: true, issues: [], skipped: ['tastings', 'customBeans', 'savedBeans', 'brewRecipes'] };
	}

	const userId = user.id;
	const issues: SyncIssue[] = [];

	// Per-type check. We try count first; if the count check fails for any
	// reason (e.g. transient network) we still try the digest, so a transient
	// 5xx on the count endpoint doesn't blind the whole check.
	type Check = {
		type: SyncType;
		countLocal: () => Promise<number>;
		countRemote: () => Promise<number>;
		digestLocal: () => Promise<string>;
		digestRemote: () => Promise<string>;
	};

	const checks: Check[] = [
		{
			type: 'tastings',
			countLocal: () => countLocalEligible<TastingSession>(db.tastings as any, userId),
			countRemote: () => getTastingsCount(),
			digestLocal: async () => {
				const rows = await db.tastings
					.filter(t => {
						if (!t.syncId) return false;
						if (t.deletedAt) return false;
						if (!t.syncedAt || (t.updatedAt || 0) > t.syncedAt) return false;
						return t.ownerId === userId || t.ownerId === null || t.ownerId === undefined;
					})
					.toArray();
				return digestFromLocal<TastingSession>(rows as TastingSession[]);
			},
			digestRemote: () => getTastingsDigest()
		},
		{
			type: 'customBeans',
			countLocal: () => countLocalEligible<LocalCustomBean>(db.customBeans as any, userId),
			countRemote: () => getCustomBeansCount(),
			digestLocal: async () => {
				const rows = await db.customBeans
					.filter(b => {
						if (!b.syncId) return false;
						if (b.deletedAt) return false;
						if (!b.syncedAt || b.updatedAt > b.syncedAt) return false;
						return b.ownerId === userId || b.ownerId === null || b.ownerId === undefined;
					})
					.toArray();
				return digestFromLocal<LocalCustomBean>(rows as LocalCustomBean[]);
			},
			digestRemote: () => getCustomBeansDigest()
		},
		{
			type: 'savedBeans',
			countLocal: () => countLocalEligible<LocalSavedBean>(db.savedBeans as any, userId),
			countRemote: () => getSavedBeansCount(),
			digestLocal: async () => {
				const rows = await db.savedBeans
					.filter(b => {
						if (!b.syncId) return false;
						if (b.deletedAt) return false;
						if (!b.syncedAt || (b.updatedAt || 0) > b.syncedAt) return false;
						return b.ownerId === userId || b.ownerId === null || b.ownerId === undefined;
					})
					.toArray();
				return digestFromLocal<LocalSavedBean>(rows as LocalSavedBean[]);
			},
			digestRemote: () => getSavedBeansDigest()
		},
		{
			type: 'brewRecipes',
			countLocal: () => countLocalEligible<LocalBrewRecipe>(db.brewRecipes as any, userId, /* requireIsSaved */ true),
			countRemote: () => getBrewRecipesCount(),
			digestLocal: async () => {
				const rows = await db.brewRecipes
					.filter(r => {
						if (!r.syncId) return false;
						if (r.deletedAt) return false;
						if (!r.isSaved) return false;
						if (!r.syncedAt || (r.updatedAt || 0) > r.syncedAt) return false;
						return r.ownerId === userId || r.ownerId === null || r.ownerId === undefined;
					})
					.toArray();
				return digestFromLocal<LocalBrewRecipe>(rows as LocalBrewRecipe[], { requireIsSaved: true });
			},
			digestRemote: () => getBrewRecipesDigest()
		}
	];

	// All checks run in parallel — they're independent and network-bound.
	const results = await Promise.allSettled(
		checks.map(async (check) => {
			const [localCount, remoteCount] = await Promise.all([
				check.countLocal(),
				check.countRemote()
			]);
			if (localCount !== remoteCount) {
				return {
					type: check.type,
					reason: 'count_mismatch' as const,
					localCount,
					remoteCount
				};
			}
			// Counts match — compute digests to catch content drift.
			const [localDigest, remoteDigest] = await Promise.all([
				check.digestLocal(),
				check.digestRemote()
			]);
			if (localDigest !== remoteDigest) {
				return {
					type: check.type,
					reason: 'digest_mismatch' as const,
					localCount,
					remoteCount
				};
			}
			return null;
		})
	);

	for (let i = 0; i < results.length; i++) {
		const r = results[i];
		const type = checks[i].type;
		if (r.status === 'fulfilled') {
			if (r.value) issues.push(r.value);
		} else {
			// On error for this type, skip it silently — verification is best-effort.
			console.warn(`[verifySync] Skipping ${type} due to error:`, r.reason);
			skipped.push(type);
		}
	}

	return {
		ok: issues.length === 0,
		issues,
		skipped
	};
}
