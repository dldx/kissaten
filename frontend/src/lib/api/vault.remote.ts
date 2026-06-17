import { command, form, getRequestEvent, query } from '$app/server';
import { redirect } from '@sveltejs/kit';
import { db } from '$lib/server/database';
import { savedBeans } from '$lib/server/database/schema';
import { eq, and, desc, gte, count, asc } from 'drizzle-orm';
import { z } from 'zod';
import { nanoid } from 'nanoid';
import { createHash } from 'node:crypto';

const saveBeanSchema = z.object({
	beanUrlPath: z.string().min(1, 'Bean URL path is required'),
	notes: z.string().optional().transform(val => val || null),
});

const updateBeanNotesSchema = z.object({
	savedBeanId: z.string().min(1, 'Saved bean ID is required'),
	notes: z.string().optional().transform(val => val || null),
});

function requireAuth() {
	const { locals } = getRequestEvent();

	if (!locals.user) {
		throw new Error('Authentication required. Please sign in to continue.');
	}

	return locals.user;
}

export const getSavedBeans = query(async () => {
	const currentUser = requireAuth();

	const beans = await db
		.select({
			id: savedBeans.id,
			beanUrlPath: savedBeans.beanUrlPath,
			notes: savedBeans.notes,
			createdAt: savedBeans.createdAt,
			updatedAt: savedBeans.updatedAt
		})
		.from(savedBeans)
		.where(eq(savedBeans.userId, currentUser.id))
		.orderBy(desc(savedBeans.updatedAt));

	return beans;
});

export const checkBeanSaved = query(z.string(), async (beanUrlPath) => {
	const { locals } = getRequestEvent();

	if (!locals.user) {
		return { saved: false, savedBeanId: null };
	}

	const [bean] = await db
		.select({
			id: savedBeans.id,
			notes: savedBeans.notes,
		})
		.from(savedBeans)
		.where(
			and(
				eq(savedBeans.userId, locals.user.id),
				eq(savedBeans.beanUrlPath, beanUrlPath),
			),
		)
		.limit(1);

	return {
		saved: !!bean,
		savedBeanId: bean?.id || null,
		notes: bean?.notes || "",
	};
});

export const saveBean = command(z.object({
	beanUrlPath: z.string().min(1, 'Bean URL path is required'),
	notes: z.string().optional(),
}), async (data) => {
	const currentUser = requireAuth();

	// Check if already saved
	const [existing] = await db
		.select({ id: savedBeans.id })
		.from(savedBeans)
		.where(and(
			eq(savedBeans.userId, currentUser.id),
			eq(savedBeans.beanUrlPath, data.beanUrlPath)
		))
		.limit(1);

	if (existing) {
		throw new Error('Bean already saved to vault');
	}

	const id = nanoid();
	await db.insert(savedBeans).values({
		id,
		userId: currentUser.id,
		beanUrlPath: data.beanUrlPath,
		notes: data.notes || null,
		createdAt: new Date(),
		updatedAt: new Date()
	});

	return { id };
});

export const unsaveBean = command(z.object({ savedBeanId: z.string() }), async (data) => {
	const currentUser = requireAuth();

	await db
		.delete(savedBeans)
		.where(and(
			eq(savedBeans.id, data.savedBeanId),
			eq(savedBeans.userId, currentUser.id)
		));
});

export const updateBeanNotes = command(z.object({
	savedBeanId: z.string().min(1, 'Saved bean ID is required'),
	notes: z.string().optional(),
}), async (data) => {
	const currentUser = requireAuth();

	await db
		.update(savedBeans)
		.set({
			notes: data.notes || null,
			updatedAt: new Date()
		})
		.where(and(
			eq(savedBeans.id, data.savedBeanId),
			eq(savedBeans.userId, currentUser.id)
		));
});

/**
 * Pull saved beans from the server that have been updated since the last sync
 */
export const pullSavedBeans = query(z.number(), async (since) => {
	const currentUser = requireAuth();

	const results = await db
		.select()
		.from(savedBeans)
		.where(and(
			eq(savedBeans.userId, currentUser.id),
			gte(savedBeans.updatedAt, new Date(since))
		))
		.orderBy(desc(savedBeans.updatedAt));

	return results.map(row => ({
		id: row.id,
		beanUrlPath: row.beanUrlPath,
		notes: row.notes,
		createdAt: row.createdAt.getTime(),
		updatedAt: row.updatedAt.getTime()
	}));
});

/**
 * Count of the user's saved beans. The server's `saved_beans` table has no
 * `deletedAt` column (removals are hard-deletes via `unsaveBean`), so we only
 * need to scope by user. Cheap index-only query used for sync consistency
 * verification.
 */
export const getSavedBeansCount = query(async () => {
	const currentUser = requireAuth();
	const [row] = await db
		.select({ c: count() })
		.from(savedBeans)
		.where(eq(savedBeans.userId, currentUser.id));
	return row?.c ?? 0;
});

/**
 * SHA-256 digest over the (syncId, updatedAt) of every saved bean owned by the
 * user, sorted by syncId so the result is identical to what the client
 * computes. Used to detect sync drift without downloading the full payload.
 */
export const getSavedBeansDigest = query(async () => {
	const currentUser = requireAuth();
	const rows = await db
		.select({ id: savedBeans.id, updatedAt: savedBeans.updatedAt })
		.from(savedBeans)
		.where(eq(savedBeans.userId, currentUser.id))
		.orderBy(asc(savedBeans.id));

	const joined = rows.map(r => `${r.id}:${r.updatedAt.getTime()}`).join('|');
	return createHash('sha256').update(joined).digest('hex');
});
