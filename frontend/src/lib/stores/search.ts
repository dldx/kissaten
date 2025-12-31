import { writable } from "svelte/store";
import { api, type CoffeeBean } from "$lib/api";
import type { SearchParams } from "$lib/api";
import { goto } from "$app/navigation";
import { browser } from "$app/environment";
import { currencyState } from "./currency.svelte";
import type { UserDefaults } from "$lib/types/userDefaults";
import { getUserDefaultRoasterLocations } from "$lib/api/profile.remote";
import { smartSearchLoader } from "./smartSearchLoader.svelte";

// Debounce helper for URL updates
let urlUpdateTimeout: ReturnType<typeof setTimeout> | null = null;
let lastUrlUpdate = 0;
const URL_UPDATE_DEBOUNCE = 100; // ms

function createSearchStore() {
	const { subscribe, set, update } = writable({
		allResults: [] as CoffeeBean[],
		metadata: {} as Record<string, any>,
		pageNumber: 1,
		totalResults: 0,
		error: "",
		searchQuery: "",
		smartSearchQuery: "",
		tastingNotesQuery: "",
		roasterFilter: [] as string[],
		roasterLocationFilter: [] as string[],
		originFilter: [] as string[],
		roastLevelFilter: "",
		roastProfileFilter: "",
		processFilter: "",
		varietyFilter: "",
		minPrice: "",
		maxPrice: "",
		minWeight: "",
		maxWeight: "",
		minElevation: "",
		maxElevation: "",
		regionFilter: "",
		producerFilter: "",
		farmFilter: "",
		inStockOnly: false,
		isDecaf: undefined as boolean | undefined,
		isSingleOrigin: undefined as boolean | undefined,
		tastingNotesOnly: false,
		sortBy: "date_added",
		sortOrder: "desc", // Newest beans first
		perPage: 10,
		smartSearchLoading: false,
		smartSearchAvailable: true,
	});

	let state: any;
	subscribe((value) => {
		state = value;
	});

	function buildSearchParams(page: number = 1): SearchParams {
		return {
			query: state.searchQuery || undefined,
			tasting_notes_query: state.tastingNotesQuery || undefined,
			roaster: state.roasterFilter.length > 0 ? state.roasterFilter : undefined,
			roaster_location:
				state.roasterLocationFilter.length > 0
					? state.roasterLocationFilter
					: undefined,
			origin: state.originFilter.length > 0 ? state.originFilter : undefined,
			region: state.regionFilter || undefined,
			producer: state.producerFilter || undefined,
			farm: state.farmFilter || undefined,
			roast_level: state.roastLevelFilter || undefined,
			roast_profile: state.roastProfileFilter || undefined,
			process: state.processFilter || undefined,
			variety: state.varietyFilter || undefined,
			min_price: state.minPrice ? parseFloat(state.minPrice) : undefined,
			max_price: state.maxPrice ? parseFloat(state.maxPrice) : undefined,
			min_weight: state.minWeight ? parseInt(state.minWeight) : undefined,
			max_weight: state.maxWeight ? parseInt(state.maxWeight) : undefined,
			min_elevation: state.minElevation
				? parseInt(state.minElevation)
				: undefined,
			max_elevation: state.maxElevation
				? parseInt(state.maxElevation)
				: undefined,
			in_stock_only: state.inStockOnly,
			is_decaf: state.isDecaf,
			is_single_origin: state.isSingleOrigin,
			page: page,
			per_page: state.perPage,
			sort_by: state.sortBy,
			sort_order: state.sortOrder,
			convert_to_currency: currencyState.selectedCurrency || undefined,
		};
	}

	function updateURL() {
		if (!browser) return;

		const params = new URLSearchParams();
		if (state.searchQuery) params.set("q", state.searchQuery);
		if (state.tastingNotesQuery)
			params.set("tasting_notes_query", state.tastingNotesQuery);
		if (state.smartSearchQuery)
			params.set("smart_query", state.smartSearchQuery);
		if (state.roasterFilter.length > 0) {
			state.roasterFilter.forEach((r: string) => params.append("roaster", r));
		}
		if (state.roasterLocationFilter.length > 0) {
			state.roasterLocationFilter.forEach((rl: string) =>
				params.append("roaster_location", rl),
			);
		}
		if (state.originFilter.length > 0) {
			state.originFilter.forEach((c: string) => params.append("origin", c));
		}
		if (state.regionFilter) {
			params.set("region", state.regionFilter);
		}
		if (state.producerFilter) {
			params.set("producer", state.producerFilter);
		}
		if (state.farmFilter) {
			params.set("farm", state.farmFilter);
		}
		if (state.roastLevelFilter)
			params.set("roast_level", state.roastLevelFilter);
		if (state.roastProfileFilter)
			params.set("roast_profile", state.roastProfileFilter);
		if (state.processFilter) params.set("process", state.processFilter);
		if (state.varietyFilter) params.set("variety", state.varietyFilter);
		if (state.minPrice) params.set("min_price", state.minPrice);
		if (state.maxPrice) params.set("max_price", state.maxPrice);
		if (state.minWeight) params.set("min_weight", state.minWeight);
		if (state.maxWeight) params.set("max_weight", state.maxWeight);
		if (state.minElevation) params.set("min_elevation", state.minElevation);
		if (state.maxElevation) params.set("max_elevation", state.maxElevation);
		if (state.inStockOnly) params.set("in_stock_only", "true");
		if (state.isDecaf !== undefined && state.isDecaf !== null)
			params.set("is_decaf", state.isDecaf.toString());
		if (
			state.isSingleOrigin !== undefined &&
			state.isSingleOrigin !== null
		)
			params.set("is_single_origin", state.isSingleOrigin.toString());
		params.set("sort_by", state.sortBy);
		params.set("sort_order", state.sortOrder);

		const newUrl = `/search${params.toString() ? "?" + params.toString() : ""}`;

		// Debounce URL updates to prevent rapid navigation
		const now = Date.now();
		if (now - lastUrlUpdate < URL_UPDATE_DEBOUNCE) {
			if (urlUpdateTimeout) clearTimeout(urlUpdateTimeout);
			urlUpdateTimeout = setTimeout(() => {
				goto(newUrl, { replaceState: true, noScroll: true });
				lastUrlUpdate = Date.now();
			}, URL_UPDATE_DEBOUNCE);
		} else {
			goto(newUrl, { replaceState: true, noScroll: true });
			lastUrlUpdate = now;
		}
	}

	async function performNewSearch() {
		update((s) => ({ ...s, pageNumber: 1, error: "" }));
		const params = buildSearchParams(1);
		const response = await api.search(params);

		if (response.success && response.data) {
			set({
				...state,
				allResults: response.data,
				metadata: response.metadata,
				totalResults: response.pagination?.total_items || 0,
			});
		} else {
			set({
				...state,
				error: response.message || "Search failed",
				allResults: [],
				totalResults: 0,
			});
		}
		updateURL();
	}

	async function loadMore() {
		if (state.allResults.length >= state.totalResults) {
			return;
		}
		update((s) => ({ ...s, pageNumber: s.pageNumber + 1 }));
		const params = buildSearchParams(state.pageNumber);
		const response = await api.search(params);
		if (response.success && response.data) {
			update((s) => ({
				...s,
				allResults: [...s.allResults, ...response.data],
				totalResults: response.pagination?.total_items || s.totalResults,
			}));
		}
	}


	async function performSmartSearch(query: string, userDefaults: UserDefaults) {
		if (!query || !state.smartSearchAvailable) return;
		update((s) => ({ ...s, smartSearchLoading: true, error: "" }));
		const smartSearchResult = await api.smartSearchParameters(query);

		if (smartSearchResult.success && smartSearchResult.searchParams) {
			const params = smartSearchResult.searchParams;
			// If the current roaster location filter is set to the user's default and the AI doesn't suggest any location, keep it that way
			// If the AI suggests different locations, override them


			const appliedDefaultRoasterLocations = (state.roasterLocationFilter.join() === userDefaults.roasterLocations.join()) &&
				!params.roaster_location
				? userDefaults.roasterLocations
				: params.roaster_location || [];

			update((s) => ({
				...s,
				searchQuery: params.query || "",
				tastingNotesQuery: params.tasting_notes_query || "",
				roasterFilter: Array.isArray(params.roaster)
					? params.roaster
					: params.roaster
						? [params.roaster]
						: [],
				roasterLocationFilter: Array.isArray(params.roaster_location)
					? params.roaster_location
					: params.roaster_location
						? [params.roaster_location]
						: appliedDefaultRoasterLocations,
				originFilter: Array.isArray(params.origin)
					? params.origin
					: params.origin
						? [params.origin]
						: [],
				regionFilter: params.region || "",
				producerFilter: params.producer || "",
				farmFilter: params.farm || "",
				roastLevelFilter: params.roast_level || "",
				roastProfileFilter: params.roast_profile || "",
				processFilter: params.process || "",
				varietyFilter: params.variety || "",
				minPrice: params.min_price?.toString() || "",
				maxPrice: params.max_price?.toString() || "",
				minWeight: params.min_weight?.toString() || "",
				maxWeight: params.max_weight?.toString() || "",
				minElevation: params.min_elevation?.toString() || "",
				maxElevation: params.max_elevation?.toString() || "",
				inStockOnly: params.in_stock_only || false,
				isDecaf: params.is_decaf ?? undefined,
				isSingleOrigin: params.is_single_origin ?? undefined,
				sortBy: params.sort_by || "name",
				sortOrder: params.sort_order || "asc",
			}));
			await performNewSearch();
		} else {
			update((s) => ({
				...s,
				error: smartSearchResult.error || "AI search failed",
			}));
			await performNewSearch();
		}
		update((s) => ({ ...s, smartSearchLoading: false }));
	}

	async function performImageSearch(image: File, userDefaults: UserDefaults) {
		if (!image) return;
		smartSearchLoader.setLoading(true);
		update((s) => ({ ...s, smartSearchLoading: true, error: "" }));
		const smartSearchResult = await api.smartImageSearchParameters(image);

		if (smartSearchResult.success && smartSearchResult.searchParams) {
			const params = smartSearchResult.searchParams;
			update((s) => ({
				...s,
				searchQuery: params.query || "",
				tastingNotesQuery: params.tasting_notes_query || "",
				roasterFilter: Array.isArray(params.roaster)
					? params.roaster
					: params.roaster
						? [params.roaster]
						: [],
				roasterLocationFilter: Array.isArray(params.roaster_location)
					? params.roaster_location
					: params.roaster_location
						? [params.roaster_location]
						: [],
				originFilter: Array.isArray(params.origin)
					? params.origin
					: params.origin
						? [params.origin]
						: [],
				regionFilter: params.region || "",
				producerFilter: params.producer || "",
				farmFilter: params.farm || "",
				roastLevelFilter: params.roast_level || "",
				roastProfileFilter: params.roast_profile || "",
				processFilter: params.process || "",
				varietyFilter: params.variety || "",
				minPrice: params.min_price?.toString() || "",
				maxPrice: params.max_price?.toString() || "",
				minWeight: params.min_weight?.toString() || "",
				maxWeight: params.max_weight?.toString() || "",
				minElevation: params.min_elevation?.toString() || "",
				maxElevation: params.max_elevation?.toString() || "",
				inStockOnly: params.in_stock_only || false,
				isDecaf: params.is_decaf ?? undefined,
				isSingleOrigin: params.is_single_origin ?? undefined,
				sortBy: "relevance",
				sortOrder: "desc",
			}));
			await performNewSearch();
		} else {
			update((s) => ({
				...s,
				error: smartSearchResult.error || "AI search failed",
			}));
			await performNewSearch();
		}
		smartSearchLoader.setLoading(false);
		update((s) => ({ ...s, smartSearchLoading: false }));
	}

	function clearFilters() {
		set({
			...state,
			searchQuery: "",
			smartSearchQuery: "",
			tastingNotesQuery: "",
			roasterFilter: [],
			roasterLocationFilter: [],
			originFilter: [],
			regionFilter: "",
			producerFilter: "",
			farmFilter: "",
			roastLevelFilter: "",
			roastProfileFilter: "",
			processFilter: "",
			varietyFilter: "",
			minPrice: "",
			maxPrice: "",
			minWeight: "",
			maxWeight: "",
			minElevation: "",
			maxElevation: "",
			inStockOnly: false,
			isDecaf: undefined,
			isSingleOrigin: undefined,
			tastingNotesOnly: false,
			sortBy: "name",
			sortOrder: "asc",
		});
		performNewSearch();
	}

	return {
		subscribe,
		set,
		performNewSearch,
		loadMore,
		performSmartSearch,
		performImageSearch,
		clearFilters,
	};
}

export const searchStore = createSearchStore();
