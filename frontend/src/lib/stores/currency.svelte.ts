import { browser } from '$app/environment';

// Helper functions for cookie management
function getCookie(name: string): string | null {
	if (!browser) return null;
	const value = `; ${document.cookie}`;
	const parts = value.split(`; ${name}=`);
	if (parts.length === 2) {
		const cookieValue = parts.pop()?.split(';').shift();
		return cookieValue || null;
	}
	return null;
}

function setCookie(name: string, value: string, days: number = 365): void {
	if (!browser) return;
	const expires = new Date();
	expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
	document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/;SameSite=Lax`;
}

// Create a class to manage currency state
class CurrencyState {
	selectedCurrency = $state<string>('');

	constructor() {
		// Initialize from cookie on creation
		if (browser) {
			const saved = getCookie('kissaten-currency');
			if (saved) {
				this.selectedCurrency = saved;
			}
		}
	}

	// Update currency and save to cookie
	setCurrency(currency: string) {
		this.selectedCurrency = currency;
		if (browser) {
			setCookie('kissaten-currency', currency);
			// Dispatch event for components that don't use the state
			window.dispatchEvent(new CustomEvent('currency-changed', {
				detail: { currency }
			}));
		}
	}
}

// Export a single instance
export const currencyState = new CurrencyState();
