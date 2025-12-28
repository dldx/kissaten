import type { Session, User } from 'better-auth'
import 'unplugin-icons/types/svelte'
// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		interface Locals {
			currency?: string;
			session?: Session;
			user?: User & {
				newsletterSubscribed?: boolean;
			};
		}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}
}

export { };
