import { z } from 'zod/mini'

export const signupSchema = z.object({
	email: z.email(),
})

export const loginSchema = z.object({
	email: z.email(),
})