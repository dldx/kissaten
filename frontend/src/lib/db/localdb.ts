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
	intensity?: Record<string, number>;
	mouthfeel?: Record<string, string>;
	basics?: Record<string, string>;
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
 * Get all saved tasting sessions, sorted by date (newest first)
 */
export async function getTastingHistory(): Promise<TastingSession[]> {
	try {
		return await db.tastings
			.orderBy('date')
			.reverse()
			.toArray();
	} catch (error) {
		console.error('Error getting tasting history:', error);
		return [];
	}
}

/**
 * Delete a specific tasting session
 */
export async function deleteTasting(id: number): Promise<void> {
	try {
		await db.tastings.delete(id);
	} catch (error) {
		console.error('Error deleting tasting session:', error);
	}
}

export { db };
