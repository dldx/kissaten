import { currencyState } from '$lib/stores/currency.svelte.js';

// Initialize the currency store so it's available everywhere
export async function load() {
	// The currency store is already initialized in its constructor
	// This ensures it's loaded at the root layout level
	return {
		currencyState
	};
}