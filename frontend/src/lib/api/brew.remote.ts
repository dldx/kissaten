import { query, getRequestEvent } from '$app/server';
import crypto from 'node:crypto';

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
