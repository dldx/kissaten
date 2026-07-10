import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/private';
import crypto from 'crypto';

export const GET: RequestHandler = async ({ request, url }) => {
	const privateKeyPem = env.BOT_PRIVATE_KEY_PEM;
	const keyId = env.BOT_KEY_ID || '7rq6iZM82v9e5xbiQumXCxMajc9zE6TZXbbM_hGcUPw';
	const publicKeyX = env.BOT_PUBLIC_KEY_X || 'iYPgodUxrqfeyAjbuvyo9NQEjHZJaAkQl-AWhSZ2mbg';

	if (!privateKeyPem) {
		console.error('BOT_PRIVATE_KEY_PEM is not configured in SvelteKit environment variables.');
		return new Response(JSON.stringify({ error: 'Key directory signature configuration missing.' }), {
			status: 500,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	// 1. Get incoming request authority/host
	const authority = request.headers.get('host') || url.host || 'kissaten.app';

	// 2. Generate timestamps, nonce
	const created = Math.floor(Date.now() / 1000);
	const expires = created + 10; // short duration per Cloudflare requirements
	const nonce = crypto.randomBytes(32).toString('base64url');

	// 3. Construct the Signature-Input header value
	const signatureInput = `sig1=("@authority";req);alg="ed25519";keyid="${keyId}";nonce="${nonce}";tag="http-message-signatures-directory";created=${created};expires=${expires}`;

	// 4. Construct the Signature Base String
	const signatureBase = `"@authority";req: ${authority}\n"@signature-params": ("@authority";req);alg="ed25519";keyid="${keyId}";nonce="${nonce}";tag="http-message-signatures-directory";created=${created};expires=${expires}`;

	let signature = '';
	try {
		// Replace escaped newlines if private key is stored as single-line string with '\n'
		const formattedKey = privateKeyPem.replace(/\\n/g, '\n');
		const privateKey = crypto.createPrivateKey({
			key: formattedKey,
			format: 'pem'
		});

		// Sign the Signature Base String using Ed25519
		const signatureBuffer = crypto.sign(null, Buffer.from(signatureBase), privateKey);
		signature = signatureBuffer.toString('base64');
	} catch (err) {
		console.error('Failed to sign HTTP response:', err);
		return new Response(JSON.stringify({ error: 'Cryptographic signature generation failed.' }), {
			status: 500,
			headers: { 'Content-Type': 'application/json' }
		});
	}

	// 5. Construct response body (JWKS format)
	const body = {
		keys: [
			{
				kty: 'OKP',
				crv: 'Ed25519',
				x: publicKeyX
			}
		]
	};

	// 6. Return response with required headers
	return new Response(JSON.stringify(body, null, 2), {
		headers: {
			'Content-Type': 'application/http-message-signatures-directory+json',
			'Signature': `sig1=:${signature}:`,
			'Signature-Input': signatureInput,
			'Cache-Control': 'public, max-age=3600, s-maxage=86400'
		}
	});
};
