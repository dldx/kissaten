import { betterAuth } from 'better-auth'
import { magicLink, emailOTP } from "better-auth/plugins";
import { drizzleAdapter } from 'better-auth/adapters/drizzle'
import { sveltekitCookies } from 'better-auth/svelte-kit'
import { db } from '$lib/server/database'
import { getRequestEvent } from '$app/server'
import { sendEmail } from '$lib/server/email'

const otpStore = new Map<string, string>();

export const auth = betterAuth({
	basePath: '/auth',
	database: drizzleAdapter(db, { provider: 'sqlite' }),
	plugins: [sveltekitCookies(getRequestEvent),

	magicLink({
		expiresIn: 60 * 5,
		sendMagicLink: async ({ email, token, url }, request) => {
			// Create custom URL at /login/verify instead of /api/auth/magic-link/verify
			const baseUrl = process.env.BETTER_AUTH_URL// || 'http://localhost:3000';

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

			// Trigger OTP generation and capture it via the emailOTP plugin's callback
			await auth.api.sendVerificationOTP({
				body: {
					email,
					type: "sign-in"
				}
			});

			const otp = otpStore.get(email) || "------";
			otpStore.delete(email); // Clean up

			void sendEmail({
				to: email,
				subject: `Your verification code: ${otp}`,
				text: `Your verification code is: ${otp}. Or click the link to sign in: ${customUrl.toString()}`,
				html: `
						<!DOCTYPE html>
						<html lang="en">
						<head>
							<meta charset="UTF-8">
							<meta name="viewport" content="width=device-width, initial-scale=1.0">
						</head>
						<body style="margin: 0; padding: 0; font-family: 'Quicksand', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #fdf8f3;">
							<table role="presentation" style="width: 100%; border-collapse: collapse;">
								<tr>
									<td align="center" style="padding: 40px 20px;">
										<table role="presentation" style="max-width: 600px; width: 100%; border-collapse: collapse; background-color: #ffffff; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);">
											<!-- Header with Logo -->
											<tr>
												<td style="padding: 40px 40px 30px; text-align: center; background: #def1e1; border-radius: 9.4px 9.4px 0 0;">
												<a href="https://kissaten.app">
													<img src="cid:logo@kissaten.app" alt="Kissaten logo" style="width: 100%; max-width: 300px; margin-bottom: 20px;">
												</a>
												<h1 style="margin: 0; color: #1a1410; font-size: 32px; font-weight: 700; letter-spacing: -0.5px; font-family: 'Knewave', sans-serif;">Sign in to Kissaten</h1>
												</td>
											</tr>

											<!-- Content -->
											<tr>
												<td style="padding: 40px; background-color: #ffffff;">
													<p style="margin: 0 0 24px; color: #3d3730; font-size: 16px; line-height: 1.6;">
														Welcome back! You can sign in using the code below or by clicking the magic link button.
													</p>

													<!-- OTP Code -->
													<div style="margin: 32px 0; text-align: center;">
														<p style="margin: 0 0 12px; color: #736b5e; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Your Verification Code</p>
														<div style="display: inline-block; padding: 20px 40px; background-color: #f8f6f3; border: 2px dashed #f2a03d; border-radius: 12px;">
															<span style="font-family: 'Courier New', monospace; font-size: 36px; font-weight: 700; color: #1a1410; letter-spacing: 8px;">${otp}</span>
														</div>
													</div>

													<div style="text-align: center; margin: 32px 0;">
														<div style="height: 1px; background-color: #e5e0d8; display: inline-block; width: 40%; vertical-align: middle;"></div>
														<span style="padding: 0 10px; color: #b5a89a; font-size: 14px; vertical-align: middle;">OR</span>
														<div style="height: 1px; background-color: #e5e0d8; display: inline-block; width: 40%; vertical-align: middle;"></div>
													</div>

													<!-- CTA Button -->
													<table role="presentation" style="width: 100%; border-collapse: collapse;">
														<tr>
															<td align="center" style="padding: 10px 0;">
																<a href="${customUrl.toString()}" style="display: inline-block; padding: 14px 36px; background: #def1e1; color: #1a1410; text-decoration: none; border-radius: 10.4px; font-weight: 600; font-size: 16px; box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08); transition: all 0.3s;">
																	Sign In via Magic Link ☕
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
															<strong>⏱️ Quick heads up:</strong> This sign-in method expires in 5 minutes for your security.
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
					`,
				attachments: [
					{
						filename: 'logo_full.png',
						path: 'static/logo_full.png',
						cid: 'logo@kissaten.app',
					}
				]
			});
		}
	}),

	emailOTP({
		sendVerificationOTP: async ({ email, otp, type }, request) => {
			// Capture the OTP so we can include it in the magic link email
			otpStore.set(email, otp);
		}
	})
	],
})