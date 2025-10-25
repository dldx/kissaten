import { z } from 'zod/mini'

export const signupSchema = z.object({
	name: z.string().check(z.minLength(4)),
	email: z.email(),
})

export const loginSchema = z.object({
	email: z.email(),
	name: z.string().check(z.minLength(1)),
})