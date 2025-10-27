import { redirect } from '@sveltejs/kit';
import { auth } from '$lib/server/auth';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ url, request, cookies }) => {
	const token = url.searchParams.get('token');
	const callbackURL = url.searchParams.get('callbackURL') || '/';

	if (!token) {
		redirect(303, '/login?error=invalid');
	}

	try {
		// Verify the magic link token using better-auth
        const response = await auth.api.magicLinkVerify({
			query: {
				token,
				callbackURL,
			},
			headers: request.headers,
		});

        // If we get here, verification was successful
        redirect(303, callbackURL);
	} catch (error) {
        // Check if it's a redirect response from better-auth (which means success)
        if (error && typeof error === 'object' && 'statusCode' in error) {
            const statusCode = (error as any).statusCode;
            const headers = (error as any).headers;

            // 302 (FOUND) and 303 (SEE OTHER) are success redirects from better-auth
            if (statusCode === 302 || statusCode === 303) {
                // Extract and set cookies from better-auth response
                if (headers && headers.get) {
                    const setCookieHeader = headers.get('set-cookie');
                    if (setCookieHeader) {
                        // Parse and set the session cookie
                        const cookieStrings = Array.isArray(setCookieHeader) ? setCookieHeader : [setCookieHeader];
                        for (const cookieString of cookieStrings) {
                            // Parse cookie string (simplified - better-auth sets the cookie properly)
                            const [nameValue] = cookieString.split(';');
                            const [name, value] = nameValue.split('=');
                            if (name && value) {
                                cookies.set(name.trim(), value.trim(), {
                                    path: '/',
                                    httpOnly: true,
                                    sameSite: 'lax',
                                    maxAge: 60 * 60 * 24 * 7, // 7 days
                                    secure: process.env.NODE_ENV === 'production'
                                });
                            }
                        }
                    }
                }

                // Now do a proper SvelteKit redirect
                redirect(303, callbackURL);
            }
		}

		// Otherwise it's a real error
		console.error('Magic link verification error:', error);
		redirect(303, '/login?error=verification_failed');
    }
};