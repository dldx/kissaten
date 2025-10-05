<script lang="ts">
	import SearchFilters from "$lib/components/search/SearchFilters.svelte";
	import SearchResults from "$lib/components/search/SearchResults.svelte";
	import { LoaderState } from "$lib/components/infinite-scroll";
	import type { PageData } from "./$types";
	import { browser } from "$app/environment";
	import { currencyState } from "$lib/stores/currency.svelte";
	import { searchStore } from "$lib/stores/search";

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// Initialize store with server-loaded data.
	// This runs on server and client, ensuring store is populated before render.
	searchStore.set({
		// Data from server
		allResults: data.searchResults,
		metadata: data.metadata,
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
		smartSearchAvailable: data.smartSearchAvailable,

		// Client-side state with default values
		pageNumber: 1,
		error: "",
		smartSearchLoading: false,
	});

	// Initialize loader state for infinite scroll
	const loaderState = new LoaderState();
	let showFilters = $state(
		browser ? (window.location.hash === "#advanced-search" ? true : false) : false,
	);

	// Track currency changes and refresh results
	let previousCurrency = $state(currencyState.selectedCurrency);
	$effect(() => {
		if (
			currencyState.selectedCurrency !== previousCurrency &&
			$searchStore.allResults.length > 0
		) {
			previousCurrency = currencyState.selectedCurrency;
			searchStore.performNewSearch();
		}
	});

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
		<h1 class="hidden mb-4 font-bold text-3xl">Coffee Beans</h1>

		<!-- Desktop Sidebar Filters -->
		<div class="{showFilters ? 'hidden lg:block' : 'hidden'}">
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
				originOptions={data.originOptions}
				allRoasters={data.allRoasters}
				roasterLocationOptions={data.roasterLocationOptions}
				onSearch={searchStore.performNewSearch}
				onClearFilters={searchStore.clearFilters}
			/>
		</div>

		<!-- Search Results with integrated filters -->
		<SearchResults
			results={$searchStore.allResults}
			maxPossibleScore={$searchStore.metadata.max_possible_score}
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
			originOptions={data.originOptions}
			allRoasters={data.allRoasters}
			roasterLocationOptions={data.roasterLocationOptions}
			onSearch={searchStore.performNewSearch}
		/>
	</div>
</div>

