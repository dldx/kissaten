// Reads the currency cookie on the server so that universal `load` functions
// in this layout subtree build identical request URLs during SSR and client
// hydration. Defaults to EUR (matching currencyState's constructor default and
// CurrencySelector's auto-default) so first-visit SSR and the client agree on
// the currency — otherwise CurrencySelector sets EUR after mount, which the
// search page's currency-change $effect interprets as a user action and
// triggers a full refetch.
import { CURRENCY_COOKIE_NAME, DEFAULT_CURRENCY } from '$lib/constants';

export const load = async ({ cookies }) => {
	return {
		currency: cookies.get(CURRENCY_COOKIE_NAME) || DEFAULT_CURRENCY
	};
};
