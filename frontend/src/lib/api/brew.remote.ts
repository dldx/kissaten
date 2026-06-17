import { command, query, getRequestEvent } from '$app/server';
import crypto from 'node:crypto';
import { db } from '$lib/server/database';
import { brewRecipes } from '$lib/server/database/schema';
import { eq, and, gte, desc, isNull, count, asc } from 'drizzle-orm';
import { z } from 'zod';

function base64url(buf: Buffer): string {
	return buf.toString('base64')
		.replace(/=/g, '')
		.replace(/\+/g, '-')
		.replace(/\//g, '_');
}

/**
 * Generates a signed, single-use, 15-minute token for requests to the backend brew recipe engine.
 */
export const getBrewToken = query(async () => {
	const { locals } = getRequestEvent();
	if (!locals.user) {
		throw new Error('Authentication required to use the Brew Assistant.');
	}

	// Verify beta privilege
	// @ts-ignore - added dynamically in better-auth fields
	const isBetaEnabled = !!locals.user.betaEnabled;
	if (!isBetaEnabled) {
		throw new Error('Access denied. The Brew Assistant is in closed beta.');
	}

	const secret = process.env.BREW_JWT_SECRET || 'kissaten_brewing_secret_signature_key_2026_change_me_in_prod';

	const header = {
		alg: 'HS256',
		typ: 'JWT'
	};

	const now = Math.floor(Date.now() / 1000);
	const exp = now + (15 * 60); // 15 mins validity

	const payload = {
		sub: locals.user.id,
		email: locals.user.email,
		iat: now,
		exp: exp
	};

	const headerStr = base64url(Buffer.from(JSON.stringify(header)));
	const payloadStr = base64url(Buffer.from(JSON.stringify(payload)));

	const signatureInput = `${headerStr}.${payloadStr}`;
	const signature = base64url(
		crypto.createHmac('sha256', secret)
			.update(signatureInput)
			.digest()
	);

	return `${signatureInput}.${signature}`;
});

function requireAuth() {
	const { locals } = getRequestEvent();
	if (!locals.user) {
		throw new Error('Authentication required. Please sign in to continue.');
	}
	return locals.user;
}

// Schema for brew recipe sync data
const recipeSyncSchema = z.object({
	id: z.string(), // This is the syncId (UUID)
	data: z.string(), // JSON string of the brew recipe
	updatedAt: z.number(),
	deletedAt: z.number().nullable().optional()
});

/**
 * Push a batch of brew recipes to the server
 * Uses last-write-wins based on updatedAt
 */
export const pushBrewRecipes = command(z.array(recipeSyncSchema), async (sessions) => {
	const currentUser = requireAuth();

	for (const session of sessions) {
		// Check if record exists
		const existing = await db
			.select()
			.from(brewRecipes)
			.where(and(
				eq(brewRecipes.id, session.id),
				eq(brewRecipes.userId, currentUser.id)
			))
			.get();

		if (!existing) {
			// Insert new
			await db.insert(brewRecipes).values({
				id: session.id,
				userId: currentUser.id,
				data: session.data,
				updatedAt: new Date(session.updatedAt),
				deletedAt: session.deletedAt ? new Date(session.deletedAt) : null
			});
		} else if (session.updatedAt > existing.updatedAt.getTime()) {
			// Update existing if newer
			await db.update(brewRecipes)
				.set({
					data: session.data,
					updatedAt: new Date(session.updatedAt),
					deletedAt: session.deletedAt ? new Date(session.deletedAt) : null
				})
				.where(eq(brewRecipes.id, session.id));
		}
	}

	return { success: true };
});

/**
 * Pull brew recipes from the server that have been updated since the last sync
 */
export const pullBrewRecipes = query(z.number(), async (since) => {
	const currentUser = requireAuth();

	const results = await db
		.select()
		.from(brewRecipes)
		.where(and(
			eq(brewRecipes.userId, currentUser.id),
			gte(brewRecipes.updatedAt, new Date(since))
		))
		.orderBy(desc(brewRecipes.updatedAt));

	return results.map(row => ({
		id: row.id,
		data: row.data,
		updatedAt: row.updatedAt.getTime(),
		deletedAt: row.deletedAt?.getTime() || null
	}));
});

/**
 * Count of the user's non-deleted brew recipes. Only recipes that have ever
 * been pushed (i.e. those the client marked `isSaved`) live on the server,
 * which already aligns with the client's sync predicate. Cheap index-only
 * query used for sync consistency verification.
 */
export const getBrewRecipesCount = query(async () => {
	const currentUser = requireAuth();
	const [row] = await db
		.select({ c: count() })
		.from(brewRecipes)
		.where(and(
			eq(brewRecipes.userId, currentUser.id),
			isNull(brewRecipes.deletedAt)
		));
	return row?.c ?? 0;
});

/**
 * SHA-256 digest over the (syncId, updatedAt) of every non-deleted brew recipe
 * owned by the user, sorted by syncId so the result is identical to what the
 * client computes. Used to detect sync drift without downloading the full payload.
 */
export const getBrewRecipesDigest = query(async () => {
	const currentUser = requireAuth();
	const rows = await db
		.select({ id: brewRecipes.id, updatedAt: brewRecipes.updatedAt })
		.from(brewRecipes)
		.where(and(
			eq(brewRecipes.userId, currentUser.id),
			isNull(brewRecipes.deletedAt)
		))
		.orderBy(asc(brewRecipes.id));

	const joined = rows.map(r => `${r.id}:${r.updatedAt.getTime()}`).join('|');
	return crypto.createHash('sha256').update(joined).digest('hex');
});
