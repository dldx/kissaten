import { createAuthClient } from 'better-auth/svelte'
import { magicLinkClient } from "better-auth/client/plugins";

export const authClient = createAuthClient({
	baseURL: 'http://localhost:3000',
	plugins: [magicLinkClient()]
})