import { browser } from '$app/environment';
import { api } from '$lib/api';

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
	rates = $state<Record<string, number>>({});

	constructor() {
		// Initialize from cookie on creation
		if (browser) {
			const saved = getCookie('kissaten-currency');
			if (saved) {
				this.selectedCurrency = saved;
			}
			this.fetchRates();
		}
	}

	async fetchRates() {
		try {
			const response = await api.getCurrencies();
			if (response.success && response.data) {
				const newRates: Record<string, number> = {};
				for (const c of response.data) {
					newRates[c.code] = c.rate_to_usd;
				}
				this.rates = newRates;
			}
		} catch (error) {
			console.error('Failed to load currency rates in CurrencyState:', error);
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

	/**
	 * Convert a price from one currency to the selected currency.
	 * If the selected currency is empty (Original) or rates aren't loaded yet,
	 * it returns the original value.
	 */
	convert(price: number | null, fromCurrency: string): { price: number; currency: string } {
		if (price === null || price === undefined) {
			return { price: 0, currency: fromCurrency || 'EUR' };
		}

		const targetCurrency = this.selectedCurrency;
		// If no target currency selected, or they match, or rates aren't loaded yet, return original
		if (!targetCurrency || fromCurrency === targetCurrency || !this.rates || Object.keys(this.rates).length === 0) {
			return { price, currency: fromCurrency || 'EUR' };
		}

		// Ensure uppercase names
		const targetUpper = targetCurrency.toUpperCase();
		const fromUpper = fromCurrency ? fromCurrency.toUpperCase() : 'EUR';

		if (fromUpper === targetUpper) {
			return { price, currency: targetUpper };
		}

		if (fromUpper === 'USD') {
			const toRate = this.rates[targetUpper];
			if (toRate) {
				return { price: price * toRate, currency: targetUpper };
			}
		} else if (targetUpper === 'USD') {
			const fromRate = this.rates[fromUpper];
			if (fromRate && fromRate !== 0) {
				return { price: price / fromRate, currency: 'USD' };
			}
		} else {
			const fromRate = this.rates[fromUpper];
			const toRate = this.rates[targetUpper];
			if (fromRate && toRate && fromRate !== 0) {
				const usdAmount = price / fromRate;
				return { price: usdAmount * toRate, currency: targetUpper };
			}
		}

		return { price, currency: fromCurrency || 'EUR' };
	}
}

// Export a single instance
export const currencyState = new CurrencyState();
