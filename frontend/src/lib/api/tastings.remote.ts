import { command, getRequestEvent, query } from '$app/server';
import { db } from '$lib/server/database';
import { tastingSessions } from '$lib/server/database/schema';
import { eq, and, gt, desc } from 'drizzle-orm';
import { z } from 'zod';

function requireAuth() {
	const { locals } = getRequestEvent();
	if (!locals.user) {
		throw new Error('Authentication required. Please sign in to continue.');
	}
	return locals.user;
}

// Schema for tasting session sync data
const tastingSyncSchema = z.object({
	id: z.string(), // This is the syncId (UUID)
	data: z.string(), // JSON string of the tasting session
	updatedAt: z.number(),
	deletedAt: z.number().nullable().optional()
});

/**
 * Push a batch of tasting sessions to the server
 * Uses last-write-wins based on updatedAt
 */
export const pushTastings = command(z.array(tastingSyncSchema), async (sessions) => {
	const currentUser = requireAuth();

	for (const session of sessions) {
		// Check if record exists
		const existing = await db
			.select()
			.from(tastingSessions)
			.where(and(
				eq(tastingSessions.id, session.id),
				eq(tastingSessions.userId, currentUser.id)
			))
			.get();

		if (!existing) {
			// Insert new
			await db.insert(tastingSessions).values({
				id: session.id,
				userId: currentUser.id,
				data: session.data,
				updatedAt: new Date(session.updatedAt),
				deletedAt: session.deletedAt ? new Date(session.deletedAt) : null
			});
		} else if (session.updatedAt > existing.updatedAt.getTime()) {
			// Update existing if newer
			await db.update(tastingSessions)
				.set({
					data: session.data,
					updatedAt: new Date(session.updatedAt),
					deletedAt: session.deletedAt ? new Date(session.deletedAt) : null
				})
				.where(eq(tastingSessions.id, session.id));
		}
	}

	return { success: true };
});

/**
 * Pull tasting sessions from the server that have been updated since the last sync
 */
export const pullTastings = query(z.number(), async (since) => {
	const currentUser = requireAuth();

	const results = await db
		.select()
		.from(tastingSessions)
		.where(and(
			eq(tastingSessions.userId, currentUser.id),
			gt(tastingSessions.updatedAt, new Date(since))
		))
		.orderBy(desc(tastingSessions.updatedAt));

	return results.map(row => ({
		id: row.id,
		data: row.data,
		updatedAt: row.updatedAt.getTime(),
		deletedAt: row.deletedAt?.getTime() || null
	}));
});
