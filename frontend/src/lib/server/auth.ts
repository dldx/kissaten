import { betterAuth } from 'better-auth'
import { magicLink } from "better-auth/plugins";
import { drizzleAdapter } from 'better-auth/adapters/drizzle'
import { sveltekitCookies } from 'better-auth/svelte-kit'
import { db } from '$lib/server/database'
import { getRequestEvent } from '$app/server'
import { sendEmail } from '$lib/server/email'

export const auth = betterAuth({
	baseURL: process.env.BETTER_AUTH_URL || 'http://localhost:3000',
	database: drizzleAdapter(db, { provider: 'sqlite' }),
	plugins: [sveltekitCookies(getRequestEvent),

        magicLink({
            sendMagicLink: async ({ email, token, url }, request) => {
				// Create custom URL at /login/verify instead of /api/auth/magic-link/verify
				const baseUrl = process.env.BETTER_AUTH_URL || 'http://localhost:3000';

				// Parse the original URL to extract callback parameters
				const originalUrl = new URL(url);
				const callbackURL = originalUrl.searchParams.get('callbackURL');
				const newUserCallbackURL = originalUrl.searchParams.get('newUserCallbackURL');
				const errorCallbackURL = originalUrl.searchParams.get('errorCallbackURL');

				// Build custom URL with all parameters
				const customUrl = new URL('/login/verify', baseUrl);
				customUrl.searchParams.set('token', token);
				if (callbackURL) customUrl.searchParams.set('callbackURL', callbackURL);
				if (newUserCallbackURL) customUrl.searchParams.set('newUserCallbackURL', newUserCallbackURL);
				if (errorCallbackURL) customUrl.searchParams.set('errorCallbackURL', errorCallbackURL);

                await sendEmail({
					to: email,
					subject: 'Sign in to Kissaten',
					text: `Click the link to sign in: ${customUrl.toString()}`,
					html: `
						<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
							<h2>Sign in to Kissaten</h2>
							<p>Click the button below to sign in to your account:</p>
							<a href="${customUrl.toString()}" style="display: inline-block; padding: 12px 24px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0;">Sign In</a>
							<p>Or copy and paste this link into your browser:</p>
							<p style="word-break: break-all; color: #666;">${customUrl.toString()}</p>
							<p style="color: #999; font-size: 12px; margin-top: 40px;">If you didn't request this email, you can safely ignore it.</p>
						</div>
					`
				});
            }
        })
    ],
	emailAndPassword: { enabled: true  }
})