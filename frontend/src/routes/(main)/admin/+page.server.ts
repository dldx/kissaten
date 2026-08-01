import { error, redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals }) => {
	if (!locals.user) {
		redirect(307, '/login');
	}

	if (locals.user.role !== 'admin') {
		// Show a friendly, non-scary error page (see /admin/+error.svelte)
		// rather than the generic destructive-styled one. Message is read
		// by the error page so it stays in plain English.
		error(403, 'This page is only available to site administrators.');
	}

	return {
		currentAdmin: {
			id: locals.user.id,
			name: locals.user.name,
			email: locals.user.email
		}
	};
};
