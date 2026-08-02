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
			role?: string;
		};
		}
		// interface PageData {}
		interface PageData {
			feedbackContext?: import('$lib/types/feedback').FeedbackContext;
		}
		// interface PageState {}
		// interface Platform {}
	}
}

export { };
