import { authClient } from "$lib/auth-client";
import { get } from "svelte/store";

class UserSettings {
	#betaEnabled = $state(false);
	#unsubscribe: (() => void) | null = null;

	constructor() {
		const session = authClient.useSession();

		// Subscribe to the Svelte store manually since auto-subscription
		// ($prefix) doesn't work in .svelte.ts files
		this.#unsubscribe = session.subscribe((value) => {
			if (value?.data?.user) {
				// @ts-ignore - added via additionalFields in auth.ts
				this.#betaEnabled = !!value.data.user.betaEnabled;
			} else {
				this.#betaEnabled = false;
			}
		});
	}

	get betaEnabled() {
		return this.#betaEnabled;
	}

	set betaEnabled(value: boolean) {
		this.#betaEnabled = value;
	}
}

export const userSettings = new UserSettings();
