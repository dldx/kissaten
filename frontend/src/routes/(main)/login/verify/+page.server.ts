import { redirect } from '@sveltejs/kit';
import { auth } from '$lib/server/auth';
import { APIError } from 'better-auth/api';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ url, request, locals }) => {
	const token = url.searchParams.get('token');
	const callbackURL = url.searchParams.get('callbackURL') || '/';

	if (!token) {
		redirect(303, '/login?error=invalid');
	}

	if (locals.user) {
		redirect(303, '/vault');
	}


	try {
		const response = await auth.api.magicLinkVerify({
			query: {
				token,
				callbackURL,

			},
			headers: request.headers,
		});

		return response

	} catch (error) {
		if (error instanceof APIError) {
			const errorRedirectURL = JSON.parse(JSON.stringify(error.headers))["location"]
			const errorType = new URL(errorRedirectURL).searchParams.get("error")
			if (errorType === null) {
				redirect(302, errorRedirectURL);
			}
			redirect(302, `/login?error=${errorType}`);
		}
	}
};