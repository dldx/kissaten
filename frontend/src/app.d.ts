import type { Session, User } from 'better-auth'
// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		interface Locals {
			currency?: string;
			session?: Session;
			user?: User;
		}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
