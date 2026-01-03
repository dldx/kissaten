import { createAuthClient } from 'better-auth/svelte'
import { magicLinkClient, emailOTPClient } from "better-auth/client/plugins";
import { browser } from "$app/environment";

export const authClient = createAuthClient({
	baseURL: browser ? window.location.origin : undefined,
	basePath: '/auth',
	plugins: [magicLinkClient(), emailOTPClient()]
})