import { form, getRequestEvent, query } from '$app/server';
import { redirect } from '@sveltejs/kit';
import { db } from '$lib/server/database';
import { user } from '$lib/server/database/schema';
import { eq } from 'drizzle-orm';
import { z } from 'zod';
import {
	notifyAdminBetaRequest,
	notifyAdminNewsletterChange,
} from '$lib/server/admin-notifications';

const updateProfileSchema = z.object({
	name: z.string()
		.min(1, 'Name is required')
		.transform(val => val.trim()),
	newsletterSubscribed: z.enum(['true', 'false']).transform(val => val === 'true'),
	betaEnabled: z.enum(['true', 'false']).transform(val => val === 'true'),
	betaInterest: z.enum(['true', 'false']).transform(val => val === 'true'),
	defaultRoasterLocations: z.string().optional().transform(val => val || null),
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
			isBetaAllowed: user.isBetaAllowed,
			betaEnabled: user.betaEnabled,
			betaInterest: user.betaInterest,
			defaultRoasterLocations: user.defaultRoasterLocations,
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

export const getUserDefaultRoasterLocations = query(async () => {
	const { locals } = getRequestEvent();

	if (!locals.user) {
		return [];
	}
	const currentUser = locals.user;

	const [profile] = await db
		.select({
			defaultRoasterLocations: user.defaultRoasterLocations
		})
		.from(user)
		.where(eq(user.id, currentUser.id))
		.limit(1);

	if (profile?.defaultRoasterLocations) {
		// Parse comma-separated location codes into array
		const defaultLocations = profile.defaultRoasterLocations.split(',').filter(Boolean);
		return defaultLocations;
	}
	return [];
});

export const updateProfile = form(updateProfileSchema, async (data) => {
	const currentUser = requireAuth();

	const [previous] = await db
		.select({
			email: user.email,
			name: user.name,
			newsletterSubscribed: user.newsletterSubscribed,
			betaInterest: user.betaInterest,
			isBetaAllowed: user.isBetaAllowed,
		})
		.from(user)
		.where(eq(user.id, currentUser.id))
		.limit(1);

	await db
		.update(user)
		.set({
			name: data.name,
			newsletterSubscribed: data.newsletterSubscribed,
			betaEnabled: data.betaEnabled ?? false,
			betaInterest: data.betaInterest,
			defaultRoasterLocations: data.defaultRoasterLocations,
			updatedAt: new Date()
		})
		.where(eq(user.id, currentUser.id));

	if (previous) {
		if (!previous.betaInterest && data.betaInterest && !previous.isBetaAllowed) {
			notifyAdminBetaRequest({
				email: previous.email,
				name: data.name ?? previous.name,
			});
		}
		if (previous.newsletterSubscribed !== data.newsletterSubscribed) {
			notifyAdminNewsletterChange({
				email: previous.email,
				name: data.name ?? previous.name,
				action: data.newsletterSubscribed ? 'subscribed' : 'unsubscribed',
			});
		}
	}

	return {
		success: true,
		name: data.name,
		newsletterSubscribed: data.newsletterSubscribed,
		betaEnabled: data.betaEnabled ?? false,
		betaInterest: data.betaInterest,
		defaultRoasterLocations: data.defaultRoasterLocations
	};
});
