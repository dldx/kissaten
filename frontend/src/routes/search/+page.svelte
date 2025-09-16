<script lang="ts">
	import SearchFilters from "$lib/components/search/SearchFilters.svelte";
	import SearchResults from "$lib/components/search/SearchResults.svelte";
	import { LoaderState } from "$lib/components/infinite-scroll";
	import { api, type Roaster } from "$lib/api.js";
	import type { PageData } from "./$types";
	import { onMount } from "svelte";
	import { browser } from "$app/environment";
	import { currencyState } from "$lib/stores/currency.svelte";
	import { searchStore } from "$lib/stores/search";

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// Initialize loader state for infinite scroll
	const loaderState = new LoaderState();
	let showFilters = $state(
		browser ? (window.location.hash === "#advanced-search" ? true : false) : false,
	);

	// Dropdown options
	let originOptions: { value: string; text: string }[] = $state([]);
	let allRoasters: Roaster[] = $state([]); // Store full roaster data with location codes
	let roasterOptions: { value: string; text: string }[] = $state([]);
	let roasterLocationOptions: { value: string; text: string }[] = $state([]);
	let dropdownOptionsLoaded = $state(false);

	// Load options when component mounts
	onMount(() => {
		loadDropdownOptions();
		checkSmartSearchHealth();
		// Initialize store with server-loaded data
		searchStore.set({
			...$searchStore,
			allResults: data.searchResults,
			totalResults: data.totalResults,
			searchQuery: data.searchParams.searchQuery,
			smartSearchQuery: data.searchParams.smartQuery || "",
			tastingNotesQuery: data.searchParams.tastingNotesQuery || "",
			roasterFilter: data.searchParams.roasterFilter || [],
			roasterLocationFilter: data.searchParams.roasterLocationFilter || [],
			originFilter: data.searchParams.originFilter || [],
			roastLevelFilter: data.searchParams.roastLevelFilter,
			roastProfileFilter: data.searchParams.roastProfileFilter,
			processFilter: data.searchParams.processFilter || "",
			varietyFilter: data.searchParams.varietyFilter || "",
			minPrice: data.searchParams.minPrice,
			maxPrice: data.searchParams.maxPrice,
			minWeight: data.searchParams.minWeight,
			maxWeight: data.searchParams.maxWeight,
			minElevation: data.searchParams.minElevation || "",
			maxElevation: data.searchParams.maxElevation || "",
			regionFilter: data.searchParams.regionFilter || "",
			producerFilter: data.searchParams.producerFilter || "",
			farmFilter: data.searchParams.farmFilter || "",
			inStockOnly: data.searchParams.inStockOnly,
			isDecaf: data.searchParams.isDecaf,
			isSingleOrigin: data.searchParams.isSingleOrigin,
			tastingNotesOnly: data.searchParams.tastingNotesOnly || false,
			sortBy: data.searchParams.sortBy || "date_added",
			sortOrder: data.searchParams.sortOrder || "random",
			perPage: data.searchParams.perPage,
		});
	});

	// Track currency changes and refresh results
	let previousCurrency = $state(currencyState.selectedCurrency);
	$effect(() => {
		if (
			currencyState.selectedCurrency !== previousCurrency &&
			$searchStore.allResults.length > 0 &&
			dropdownOptionsLoaded
		) {
			previousCurrency = currencyState.selectedCurrency;
			searchStore.performNewSearch();
		}
	});

	// Load dropdown options on component mount
	async function loadDropdownOptions() {
		try {
			// Load countries
			const countriesResponse = await api.getCountries();
			if (countriesResponse.success && countriesResponse.data) {
				originOptions = countriesResponse.data.map((country) => ({
					value: country.country_code,
					text: country.country_name || country.country_code,
				}));
			}

			// Load all roasters with location codes
			const roastersResponse = await api.getRoasters();
			if (roastersResponse.success && roastersResponse.data) {
				allRoasters = roastersResponse.data;
				roasterOptions = roastersResponse.data.map((roaster) => ({
					value: roaster.name,
					text: roaster.name,
				}));
			}

			// Load roaster locations
			const roasterLocationsResponse = await api.getRoasterLocations();
			if (roasterLocationsResponse.success && roasterLocationsResponse.data) {
				roasterLocationOptions = roasterLocationsResponse.data.map(
					(location) => ({
						value: location.code,
						text: `${location.code} - ${location.location} (${location.roaster_count})`,
					}),
				);
			}
			dropdownOptionsLoaded = true;
		} catch (error) {
			console.error("Error loading dropdown options:", error);
			dropdownOptionsLoaded = true; // Set to true even on error to avoid blocking UI
		}
	}

	// Check if AI search is available
	async function checkSmartSearchHealth() {
		try {
			const response = await api.smartSearchHealth();
			searchStore.set({ ...$searchStore, smartSearchAvailable: response.success });
		} catch (error) {
			console.warn("AI search service not available:", error);
			searchStore.set({ ...$searchStore, smartSearchAvailable: false });
		}
	}

	// Load more results for infinite scroll
	const loadMore = async () => {
		try {
			await searchStore.loadMore();
			if ($searchStore.allResults.length >= $searchStore.totalResults) {
				loaderState.complete();
			} else {
				loaderState.loaded();
			}
		} catch (err) {
			console.error("Error loading more results:", err);
			loaderState.error();
		}
	};

	$effect(() => {
		if ($searchStore.allResults.length >= $searchStore.totalResults) {
			loaderState.complete();
		} else {
			loaderState.reset();
		}
	});

	// Check if any filters are applied
	const hasFiltersApplied = $derived(
		!!(
			$searchStore.searchQuery ||
			$searchStore.tastingNotesQuery ||
			$searchStore.roasterFilter.length > 0 ||
			$searchStore.roasterLocationFilter.length > 0 ||
			$searchStore.originFilter.length > 0 ||
			$searchStore.regionFilter ||
			$searchStore.producerFilter ||
			$searchStore.farmFilter ||
			$searchStore.roastLevelFilter ||
			$searchStore.roastProfileFilter ||
			$searchStore.processFilter.length > 0 ||
			$searchStore.varietyFilter.length > 0 ||
			$searchStore.minPrice ||
			$searchStore.maxPrice ||
			$searchStore.minWeight ||
			$searchStore.maxWeight ||
			$searchStore.minElevation ||
			$searchStore.maxElevation ||
			$searchStore.inStockOnly ||
			$searchStore.isDecaf ||
			$searchStore.isSingleOrigin ||
			$searchStore.tastingNotesOnly
		),
	);
</script>

<svelte:head>
	<title>Search Coffee Beans - Kissaten</title>
	<meta
		name="description"
		content="Search and discover coffee beans from roasters worldwide"
	/>
</svelte:head>

<div class="mx-auto px-4 py-8 container">
	<div class="flex lg:flex-row flex-col gap-2 lg:gap-8">
		<!-- Mobile title -->
		<h1 class="lg:hidden block mb-4 font-bold text-3xl">Coffee Beans</h1>

		<!-- Desktop Sidebar Filters -->
		<div class="hidden lg:block">
			<SearchFilters
				bind:searchQuery={$searchStore.searchQuery}
				bind:tastingNotesQuery={$searchStore.tastingNotesQuery}
				bind:roasterFilter={$searchStore.roasterFilter}
				bind:roasterLocationFilter={$searchStore.roasterLocationFilter}
				bind:originFilter={$searchStore.originFilter}
				bind:roastLevelFilter={$searchStore.roastLevelFilter}
				bind:roastProfileFilter={$searchStore.roastProfileFilter}
				bind:processFilter={$searchStore.processFilter}
				bind:varietyFilter={$searchStore.varietyFilter}
				bind:minPrice={$searchStore.minPrice}
				bind:maxPrice={$searchStore.maxPrice}
				bind:minWeight={$searchStore.minWeight}
				bind:maxWeight={$searchStore.maxWeight}
				bind:minElevation={$searchStore.minElevation}
				bind:maxElevation={$searchStore.maxElevation}
				bind:regionFilter={$searchStore.regionFilter}
				bind:producerFilter={$searchStore.producerFilter}
				bind:farmFilter={$searchStore.farmFilter}
				bind:inStockOnly={$searchStore.inStockOnly}
				bind:isDecaf={$searchStore.isDecaf}
				bind:isSingleOrigin={$searchStore.isSingleOrigin}
				bind:sortBy={$searchStore.sortBy}
				bind:sortOrder={$searchStore.sortOrder}
				bind:showFilters
				{originOptions}
				{allRoasters}
				{roasterLocationOptions}
				onSearch={searchStore.performNewSearch}
				onClearFilters={searchStore.clearFilters}
			/>
		</div>

		<!-- Search Results with mobile integrated filters -->
		<SearchResults
			results={$searchStore.allResults}
			totalResults={$searchStore.totalResults}
			{loaderState}
			error={$searchStore.error}
			{hasFiltersApplied}
			onLoadMore={loadMore}
			onClearFilters={searchStore.clearFilters}
			onRetrySearch={searchStore.performNewSearch}
			bind:smartSearchValue={$searchStore.smartSearchQuery}
			smartSearchLoading={$searchStore.smartSearchLoading}
			smartSearchAvailable={$searchStore.smartSearchAvailable}
			onSmartSearch={searchStore.performSmartSearch}
			onImageSearch={searchStore.performImageSearch}
			bind:searchQuery={$searchStore.searchQuery}
			bind:tastingNotesQuery={$searchStore.tastingNotesQuery}
			bind:roasterFilter={$searchStore.roasterFilter}
			bind:roasterLocationFilter={$searchStore.roasterLocationFilter}
			bind:originFilter={$searchStore.originFilter}
			bind:roastLevelFilter={$searchStore.roastLevelFilter}
			bind:roastProfileFilter={$searchStore.roastProfileFilter}
			bind:processFilter={$searchStore.processFilter}
			bind:varietyFilter={$searchStore.varietyFilter}
			bind:minPrice={$searchStore.minPrice}
			bind:maxPrice={$searchStore.maxPrice}
			bind:minWeight={$searchStore.minWeight}
			bind:maxWeight={$searchStore.maxWeight}
			bind:minElevation={$searchStore.minElevation}
			bind:maxElevation={$searchStore.maxElevation}
			bind:regionFilter={$searchStore.regionFilter}
			bind:producerFilter={$searchStore.producerFilter}
			bind:farmFilter={$searchStore.farmFilter}
			bind:inStockOnly={$searchStore.inStockOnly}
			bind:isDecaf={$searchStore.isDecaf}
			bind:isSingleOrigin={$searchStore.isSingleOrigin}
			bind:sortBy={$searchStore.sortBy}
			bind:sortOrder={$searchStore.sortOrder}
			bind:showFilters
			{originOptions}
			{allRoasters}
			{roasterLocationOptions}
			onSearch={searchStore.performNewSearch}
		/>
	</div>
</div>

