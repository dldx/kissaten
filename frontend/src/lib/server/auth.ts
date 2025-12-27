import { betterAuth } from 'better-auth'
import { magicLink } from "better-auth/plugins";
import { drizzleAdapter } from 'better-auth/adapters/drizzle'
import { sveltekitCookies } from 'better-auth/svelte-kit'
import { db } from '$lib/server/database'
import { getRequestEvent } from '$app/server'
import { sendEmail } from '$lib/server/email'

export const auth = betterAuth({
	basePath: '/auth',
	database: drizzleAdapter(db, { provider: 'sqlite' }),
	user: {
		changeEmail: {
			enabled: true,
			sendChangeEmailConfirmation: async ({ user, newEmail, url, token }, request) => {
				void sendEmail({
					to: user.email, // Sent to the CURRENT email
					subject: 'Approve email change',
					text: `Click the link to approve the change to ${newEmail}: ${url}`
				})
			}
		}
	},
	emailVerification: {
		// Required to send the verification email
		sendVerificationEmail: async ({ user, url, token }) => {
			void sendEmail({
				to: user.email,
			})
		}
	}
	plugins: [sveltekitCookies(getRequestEvent),

	magicLink({
		expiresIn: 60 * 5,
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


			void sendEmail({
				to: email,
				subject: 'Sign in to Kissaten',
				text: `Click the link to sign in: ${customUrl.toString()}`,
				html: `
						<!DOCTYPE html>
						<html lang="en">
						<head>
							<meta charset="UTF-8">
							<meta name="viewport" content="width=device-width, initial-scale=1.0">
						</head>
						<body style="margin: 0; padding: 0; font-family: 'Quicksand', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #fdf8f3;">
							<table role="presentation" style="width: 100%; border-collapse: collapse; background-color: #fdf8f3;">
								<tr>
									<td align="center" style="padding: 40px 20px;">
										<table role="presentation" style="max-width: 600px; width: 100%; border-collapse: collapse; background-color: #ffffff; border-radius: 10.4px; border: 1px solid #d4d0c8; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);">
											<!-- Header with Logo -->
											<tr>
												<td style="padding: 40px 40px 30px; text-align: center; background: #f2a03d; border-radius: 9.4px 9.4px 0 0;">
													<img src="https://kissaten.app/logo_dark_full.svg" alt="Kissaten logo" style="width: 120px; height: 120px; margin-bottom: 20px;">
													<h1 style="margin: 0; color: #1a1410; font-size: 32px; font-weight: 700; letter-spacing: -0.5px; font-family: 'Knewave', sans-serif;">Sign in to Kissaten</h1>
												</td>
											</tr>

											<!-- Content -->
											<tr>
												<td style="padding: 40px; background-color: #ffffff;">
													<p style="margin: 0 0 24px; color: #3d3730; font-size: 16px; line-height: 1.6;">
														Welcome back! Click the button below to securely sign in to your Kissaten account and continue discovering amazing coffee beans.
													</p>

													<!-- CTA Button -->
													<table role="presentation" style="width: 100%; border-collapse: collapse;">
														<tr>
															<td align="center" style="padding: 20px 0;">
																<a href="${customUrl.toString()}" style="display: inline-block; padding: 14px 36px; background: #f2a03d; color: #1a1410; text-decoration: none; border-radius: 10.4px; font-weight: 600; font-size: 16px; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08); transition: all 0.3s;">
																	Sign In to Kissaten ☕
																</a>
															</td>
														</tr>
													</table>

													<p style="margin: 28px 0 8px; color: #736b5e; font-size: 14px; line-height: 1.6;">
														Or copy and paste this link into your browser:
													</p>
													<p style="margin: 0; padding: 14px; background-color: #f8f6f3; border-radius: 10.4px; border: 1px solid #e5e0d8; word-break: break-all; color: #8b7355; font-size: 13px; font-family: 'Courier New', monospace; line-height: 1.5;">
														${customUrl.toString()}
													</p>

													<div style="margin: 32px 0 0; padding: 16px; background-color: #f0f9f4; border-radius: 10.4px; border: 1px solid #4caf50;">
														<p style="margin: 0; color: #2d5a3d; font-size: 13px; line-height: 1.6;">
															<strong>⏱️ Quick heads up:</strong> This magic link expires in 5 minutes for your security.
														</p>
													</div>
												</td>
											</tr>

											<!-- Footer -->
											<tr>
												<td style="padding: 28px 40px; background-color: #faf8f5; border-radius: 0 0 9.4px 9.4px; text-align: center; border-top: 1px solid #e5e0d8;">
													<p style="margin: 0 0 12px; color: #8c8376; font-size: 13px; line-height: 1.5;">
														Didn't request this? No worries—you can safely ignore this email.
													</p>
													<p style="margin: 0; font-size: 13px;">
														<a href="https://kissaten.app" style="color: #f2a03d; text-decoration: none; font-weight: 600;">kissaten.app</a>
														<span style="color: #b5a89a; margin: 0 8px;">•</span>
														<span style="color: #8c8376;">Your coffee bean discovery platform</span>
													</p>
												</td>
											</tr>
										</table>
									</td>
								</tr>
							</table>
						</body>
						</html>
					`
			});
		}
	})
	],
})