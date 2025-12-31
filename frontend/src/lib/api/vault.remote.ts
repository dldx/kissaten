import { command, form, getRequestEvent, query } from '$app/server';
import { redirect } from '@sveltejs/kit';
import { db } from '$lib/server/database';
import { savedBeans } from '$lib/server/database/schema';
import { eq, and } from 'drizzle-orm';
import { z } from 'zod';
import { nanoid } from 'nanoid';

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
		.orderBy(savedBeans.createdAt);

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
