import { form, getRequestEvent, query } from '$app/server';
import { redirect } from '@sveltejs/kit';
import { db } from '$lib/server/database';
import { user } from '$lib/server/database/schema';
import { eq } from 'drizzle-orm';
import { z } from 'zod';

const updateProfileSchema = z.object({
	name: z.string()
		.min(1, 'Name is required')
		.transform(val => val.trim()),
	newsletterSubscribed: z.enum(['true', 'false']).transform(val => val === 'true'),
});

function requireAuth() {
	const { locals } = getRequestEvent();

	if (!locals.user) {
		redirect(307, '/login');
	}

	return locals.user;
}

export const getProfile = query(async () => {
	const currentUser = requireAuth();

	const [profile] = await db
		.select({
			id: user.id,
			name: user.name,
			email: user.email,
			newsletterSubscribed: user.newsletterSubscribed,
			createdAt: user.createdAt,
			updatedAt: user.updatedAt
		})
		.from(user)
		.where(eq(user.id, currentUser.id))
		.limit(1);

	if (!profile) {
		redirect(307, '/login');
	}

	return profile;
});

export const updateProfile = form(updateProfileSchema, async (data) => {
	const currentUser = requireAuth();

	await db
		.update(user)
		.set({
			name: data.name,
			newsletterSubscribed: data.newsletterSubscribed,
			updatedAt: new Date()
		})
		.where(eq(user.id, currentUser.id));

	return {
		success: true,
		name: data.name,
		newsletterSubscribed: data.newsletterSubscribed
	};
});
