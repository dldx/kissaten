// Reads the currency cookie on the server so that universal `load` functions
// in this layout subtree build identical request URLs during SSR and client
// hydration. Defaults to EUR (matching currencyState's constructor default and
// CurrencySelector's auto-default) so first-visit SSR and the client agree on
// the currency — otherwise CurrencySelector sets EUR after mount, which the
// search page's currency-change $effect interprets as a user action and
// triggers a full refetch.
//
// `getUserDefaultRoasterLocations` is a remote `query` that we invoke here on
// the server (rather than in the universal `+layout.ts`) so it doesn't fire a
// client-side `/_app/remote` fetch via `window.fetch` on navigation.
import { CURRENCY_COOKIE_NAME, DEFAULT_CURRENCY } from '$lib/constants';
import { getUserDefaultRoasterLocations } from '$lib/api/profile.remote';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ cookies }) => {
	const [currency, roasterLocations] = await Promise.all([
		cookies.get(CURRENCY_COOKIE_NAME) || DEFAULT_CURRENCY,
		getUserDefaultRoasterLocations()
	]);

	return {
		currency,
		userDefaults: {
			roasterLocations
		}
	};
};

