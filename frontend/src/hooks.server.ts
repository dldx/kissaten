import type { HandleFetch } from '@sveltejs/kit';


import { svelteKitHandler } from 'better-auth/svelte-kit'
import { auth } from '$lib/server/auth'
import { building } from '$app/environment'
import type { Handle } from '@sveltejs/kit'

export const handleFetch: HandleFetch = async ({ event, request, fetch }) => {
	// Get the currency from cookies
	const currency = event.cookies.get('kissaten-currency');

	// Store currency in locals for access in routes
	event.locals.currency = currency || '';

	// Intercept API requests and add currency conversion parameter
	if (request.url.includes('/api/v1/')) {
		// Only add currency conversion to certain endpoints that support it
		const supportsCurrencyConversion = [
			'/api/v1/search',
			'/api/v1/beans/',
			'/api/v1/processes/',
			'/api/v1/varietals/',
			'/api/v1/origins/'
		].some(path => request.url.includes(path));

		if (supportsCurrencyConversion && currency) {
			// Extract existing URL parameters
			const url = new URL(request.url);
			// Add convert_to_currency parameter if not already present
			if (!url.searchParams.has('convert_to_currency')) {
				url.searchParams.set('convert_to_currency', currency);
			}
			// Create a new Request with the updated URL
			request = new Request(url.toString(), request);
		}
	}

	return fetch(request);
};

export const handle: Handle = async ({ event, resolve }) => {
	const session = await auth.api.getSession({
		headers: event.request.headers,
	})

	if (session) {
		event.locals.session = session.session
		event.locals.user = session.user
	}

	return svelteKitHandler({ event, resolve, auth, building })
}
