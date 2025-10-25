import { redirect } from '@sveltejs/kit'
import { form, getRequestEvent, query } from '$app/server'
import { auth } from '$lib/server/auth'
import { signupSchema, loginSchema } from '$lib/schema/auth'

export const loginOrSignup = form(loginSchema, async (user) => {
	const { request } = getRequestEvent()
	await auth.api.signInMagicLink({
		body: {
			email: user.email,
			name: user.name,
			callbackURL: "/",
			newUserCallbackURL: "/",
			errorCallbackURL: "/login?error=verification_failed",
		},
		// This endpoint requires session cookies.
		headers: request.headers,
	})
	redirect(303, `/login/check-email?email=${encodeURIComponent(user.email)}`)
})

export const signout = form(async () => {
	const { request } = getRequestEvent()
	await auth.api.signOut({ headers: request.headers })
	redirect(303, '/')
})

export const getUser = query(async () => {
	const { locals } = getRequestEvent()
	if (!locals.user) {
		redirect(307, '/auth/login')
	}
	return locals.user
})