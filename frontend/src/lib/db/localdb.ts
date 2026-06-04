import Dexie, { type EntityTable } from 'dexie';
import type { CoffeeBean } from '$lib/api';

export interface RecentlyViewedBean {
	id?: number;
	beanUrlPath: string;
	viewedAt: Date;
	beanData: CoffeeBean; // Store full bean details
}

export interface TastingSession {
	id?: number;
	date: Date;
	name?: string; // Optional custom name
	brewingNotes?: string; // Optional brewing notes
	selectedNotes: string[];
	sourceBean?: string; // Optional bean title/ID if tasting a specific bean
	beanUrlPath?: string; // Optional bean URL path for linking
	beanName?: string; // Optional bean display name
	roasterName?: string; // Optional roaster display name
	beanData?: CoffeeBean; // Store full bean details when selected
	intensity?: Record<string, number>;
	mouthfeel?: Record<string, string>;
	basics?: Record<string, string>;
	// Sync fields
	syncId?: string; // UUID for cross-device identification
	updatedAt?: number; // Last modification timestamp
	deletedAt?: number | null; // Soft delete timestamp
	syncedAt?: number | null; // Last successful sync timestamp
	ownerId?: string | null; // User ID who owns this session (null = guest/unassigned)
}

const db = new Dexie('KissatenDB') as Dexie & {
	recentlyViewed: EntityTable<RecentlyViewedBean, 'id'>;
	tastings: EntityTable<TastingSession, 'id'>;
};

// Schema declaration
db.version(1).stores({
	recentlyViewed: '++id, beanUrlPath, viewedAt'
});

db.version(2).stores({
	recentlyViewed: '++id, beanUrlPath, viewedAt',
	tastings: '++id, date'
});

db.version(3).stores({
	recentlyViewed: '++id, beanUrlPath, viewedAt',
	tastings: '++id, date, name'
});

db.version(4).stores({
	recentlyViewed: '++id, beanUrlPath, viewedAt',
	tastings: '++id, date, name'
});

db.version(5).stores({
	recentlyViewed: '++id, beanUrlPath, viewedAt',
	tastings: '++id, date, name, beanUrlPath'
});

db.version(6).stores({
	recentlyViewed: '++id, beanUrlPath, viewedAt',
	tastings: '++id, date, name, beanUrlPath, syncId, updatedAt'
}).upgrade(async (tx) => {
	// Backfill existing records with sync IDs and timestamps
	await tx.table('tastings').toCollection().modify((t: TastingSession) => {
		if (!t.syncId) t.syncId = crypto.randomUUID();
		if (!t.updatedAt) {
			// Use session date as fallback, or current time
			t.updatedAt = t.date ? new Date(t.date).getTime() : Date.now();
		}
		if (t.deletedAt === undefined) t.deletedAt = null;
		if (t.syncedAt === undefined) t.syncedAt = null;
	});
});

db.version(7).stores({
	recentlyViewed: '++id, beanUrlPath, viewedAt',
	tastings: '++id, date, name, beanUrlPath, syncId, updatedAt, ownerId'
}).upgrade(async (tx) => {
	// Backfill ownerId as null (guest/unassigned) for existing records
	await tx.table('tastings').toCollection().modify((t: TastingSession) => {
		if (t.ownerId === undefined) t.ownerId = null;
	});
});

/**
 * Track a bean view in the local database
 * Updates the timestamp and bean data if already exists, otherwise creates new entry
 * Keeps all view history with full bean details
 */
export async function trackBeanView(beanData: CoffeeBean): Promise<void> {
	try {
		const beanUrlPath = beanData.bean_url_path;
		if (!beanUrlPath) {
			console.error('Bean URL path is required');
			return;
		}

		// Check if bean already exists
		const existing = await db.recentlyViewed
			.where('beanUrlPath')
			.equals(beanUrlPath)
			.first();

		if (existing) {
			// Update the viewed timestamp and bean data
			await db.recentlyViewed.update(existing.id!, {
				viewedAt: new Date(),
				beanData
			});
		} else {
			// Add new entry
			await db.recentlyViewed.add({
				beanUrlPath,
				viewedAt: new Date(),
				beanData
			});
		}
	} catch (error) {
		console.error('Error tracking bean view:', error);
	}
}

/**
 * Get recently viewed beans from the local database
 * Returns all recently viewed beans, sorted by most recent first
 */
export async function getRecentlyViewedBeans(): Promise<RecentlyViewedBean[]> {
	try {
		return await db.recentlyViewed
			.orderBy('viewedAt')
			.reverse()
			.toArray();
	} catch (error) {
		console.error('Error getting recently viewed beans:', error);
		return [];
	}
}

/**
 * Clear all recently viewed beans
 */
export async function clearRecentlyViewed(): Promise<void> {
	try {
		await db.recentlyViewed.clear();
	} catch (error) {
		console.error('Error clearing recently viewed beans:', error);
	}
}

/**
 * Get the current user ID for scoping local queries.
 * Returns the user ID from localStorage (set during sync) or null for guests.
 */
export function getCurrentOwnerId(): string | null {
	if (typeof localStorage === 'undefined') return null;
	return localStorage.getItem('kissaten_current_user_id') || null;
}

/**
 * Set the current owner ID (called on login/sync)
 */
export function setCurrentOwnerId(userId: string | null): void {
	if (typeof localStorage === 'undefined') return;
	if (userId) {
		localStorage.setItem('kissaten_current_user_id', userId);
	} else {
		localStorage.removeItem('kissaten_current_user_id');
	}
}

/**
 * Assign unowned local tastings to a user (called on first sync after login)
 */
export async function claimUnownedTastings(userId: string): Promise<void> {
	try {
		await db.tastings
			.where('ownerId')
			.equals('')
			.or('ownerId')
			.equals(null as any)
			.modify({ ownerId: userId });
	} catch (error) {
		// Fallback: filter and modify all unowned
		await db.tastings
			.filter(t => !t.ownerId)
			.modify({ ownerId: userId });
	}
}

/**
 * Get all saved tasting sessions, sorted by date (newest first)
 * Only returns sessions belonging to the current user (or unowned guest sessions)
 */
export async function getTastingHistory(): Promise<TastingSession[]> {
	try {
		const currentOwner = getCurrentOwnerId();
		return await db.tastings
			.filter(t => {
				// Filter out deleted records
				if (t.deletedAt) return false;
				// Show records belonging to current user OR unowned (guest) records
				return !t.ownerId || t.ownerId === currentOwner;
			})
			.reverse()
			.sortBy('date');
	} catch (error) {
		console.error('Error getting tasting history:', error);
		return [];
	}
}

/**
 * Get all tasting sessions for a specific bean
 * Only returns sessions belonging to the current user (or unowned guest sessions)
 */
export async function getTastingsForBean(beanUrlPath: string): Promise<TastingSession[]> {
	try {
		const currentOwner = getCurrentOwnerId();
		return await db.tastings
			.where('beanUrlPath')
			.equals(beanUrlPath)
			.filter(t => {
				if (t.deletedAt) return false;
				return !t.ownerId || t.ownerId === currentOwner;
			})
			.reverse()
			.sortBy('date');
	} catch (error) {
		console.error('Error getting tastings for bean:', error);
		return [];
	}
}

/**
 * Delete a specific tasting session
 * Soft-deletes if it has a syncId, so the deletion can be synchronized
 */
export async function deleteTasting(id: number): Promise<void> {
	try {
		const session = await db.tastings.get(id);
		if (session) {
			// If it's a transient session not synced yet, we can hard delete
			if (!session.syncedAt) {
				await db.tastings.delete(id);
			} else {
				// Soft delete: mark as deleted and update timestamp
				await db.tastings.update(id, {
					deletedAt: Date.now(),
					updatedAt: Date.now(),
				});
			}
		}
	} catch (error) {
		console.error('Error deleting tasting session:', error);
	}
}

/**
 * Get a specific tasting session by ID
 */
export async function getTasting(id: number): Promise<TastingSession | undefined> {
	try {
		const session = await db.tastings.get(id);
		if (session?.deletedAt) return undefined;
		// Check ownership
		const currentOwner = getCurrentOwnerId();
		if (session?.ownerId && session.ownerId !== currentOwner) return undefined;
		return session;
	} catch (error) {
		console.error('Error getting tasting session:', error);
		return undefined;
	}
}

export { db };
