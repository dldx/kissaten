import { redirect } from '@sveltejs/kit';
import { auth } from '$lib/server/auth';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ url, request }) => {
	const token = url.searchParams.get('token');
	const callbackURL = url.searchParams.get('callbackURL') || '/';

	if (!token) {
		redirect(303, '/login?error=invalid');
	}

	try {
		// Verify the magic link token using better-auth
		await auth.api.magicLinkVerify({
			query: {
				token,
				callbackURL,
			},
			headers: request.headers,
		});
	} catch (error) {
		// Check if it's a redirect (which means success)
		if (error && typeof error === 'object' && 'status' in error && error.status === 303) {
			// Re-throw the redirect to let SvelteKit handle it
			throw error;
		}

		// Otherwise it's a real error
		console.error('Magic link verification error:', error);
		redirect(303, '/login?error=verification_failed');
	}

	// If we reach here without a redirect, redirect to callback URL as fallback
	redirect(303, callbackURL);
};
