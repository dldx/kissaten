/**
 * Shared loading state for SmartSearch
 * Used to trigger the global page loader when SmartSearch is processing
 */
export const smartSearchLoader = (() => {
	let isLoading = $state(false);

	return {
		get isLoading() {
			return isLoading;
		},
		setLoading(value: boolean) {
			isLoading = value;
		}
	};
})();
