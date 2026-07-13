import { browser } from '$app/environment';
import { api } from '$lib/api';
import {
	CURRENCY_COOKIE_NAME,
	DEFAULT_CURRENCY,
	RATES_CACHE_KEY,
	RATES_TTL_MS
} from '$lib/constants';

interface CachedRates {
	rates: Record<string, number>;
	fetchedAt: number;
}

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

/**
 * Read cached currency rates from localStorage. Returns null if missing,
 * malformed, or older than RATES_TTL_MS. Synchronous so the CurrencyState
 * constructor can populate `rates` before any component reads it on repeat
 * visits, removing the rates network request from the critical render path.
 */
function loadCachedRates(): Record<string, number> | null {
	if (!browser) return null;
	try {
		const raw = localStorage.getItem(RATES_CACHE_KEY);
		if (!raw) return null;
		const parsed = JSON.parse(raw) as CachedRates;
		if (
			!parsed ||
			typeof parsed.fetchedAt !== 'number' ||
			typeof parsed.rates !== 'object' ||
			parsed.rates === null
		) {
			return null;
		}
		if (Date.now() - parsed.fetchedAt > RATES_TTL_MS) return null;
		return parsed.rates;
	} catch {
		return null;
	}
}

/**
 * Persist the latest rates to localStorage with the current timestamp so a
 * subsequent session can reuse them without a network round-trip.
 */
function persistRates(rates: Record<string, number>): void {
	if (!browser) return;
	try {
		const payload: CachedRates = { rates, fetchedAt: Date.now() };
		localStorage.setItem(RATES_CACHE_KEY, JSON.stringify(payload));
	} catch {
		// Quota exceeded / private mode — non-fatal; rates stay in-memory only.
	}
}

// Create a class to manage currency state
class CurrencyState {
	selectedCurrency = $state<string>('');
	rates = $state<Record<string, number>>({});
	/** True once rates are available (from cache or network). Drives the
	 *  CurrencySelector's disabled state via a simple boolean $state that
	 *  reliably triggers $derived re-evaluation (unlike Object.keys() on a
	 *  $state proxy, which can miss mutations). */
	ratesLoaded = $state(false);

	constructor() {
		// Initialize from cookie on creation, defaulting to EUR so that SSR
		// (which defaults to EUR via +layout.server.ts) and the client agree
		// on the currency before the CurrencySelector even mounts. Without
		// this, CurrencySelector auto-defaults to EUR on first visit, which
		// changes selectedCurrency after hydration and triggers a redundant
		// search refetch on the search page.
		if (browser) {
			const saved = getCookie(CURRENCY_COOKIE_NAME);
			this.selectedCurrency = saved || DEFAULT_CURRENCY;
			// Populate rates synchronously from the localStorage cache so that
			// `convert()` works immediately on repeat visits without waiting
			// for the network. On a cold cache (first visit or expired TTL),
			// `rates` stays {} and is filled by fetchRates() below.
			const cached = loadCachedRates();
			if (cached) {
				this.rates = cached;
				this.ratesLoaded = true;
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
				this.ratesLoaded = true;
				persistRates(newRates);
			}
		} catch (error) {
			// On error, still mark as loaded so the selector isn't stuck
			// disabled forever — the user can retry by changing currency.
			this.ratesLoaded = true;
			console.error('Failed to load currency rates in CurrencyState:', error);
		}
	}

	// Update currency and save to cookie
	setCurrency(currency: string) {
		this.selectedCurrency = currency;
		if (browser) {
			setCookie(CURRENCY_COOKIE_NAME, currency);
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
