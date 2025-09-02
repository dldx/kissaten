<script lang="ts">
	import { goto } from '$app/navigation';
	import SearchFilters from "$lib/components/search/SearchFilters.svelte";
	import SearchResults from "$lib/components/search/SearchResults.svelte";
	import { InfiniteLoader, LoaderState } from "$lib/components/infinite-scroll";
	import { api, type CoffeeBean, type APIResponse, type Country, type RoasterLocation, type Roaster } from '$lib/api.js';
	import type { PageData } from './$types';
    import { onMount } from 'svelte';

	interface Props {
		data: PageData;
	}



	let { data }: Props = $props();

	// Initialize loader state for infinite scroll
	const loaderState = new LoaderState();

	// Initialize search results with loaded data
	let allResults: CoffeeBean[] = $state(data.searchResults);
	let pageNumber = $state(1);
	let totalResults = $state(data.totalResults);
	let error = $state('');
	let showFilters = $state(false);

	// Search parameters from loaded data
	let searchQuery = $state(data.searchParams.searchQuery);
	let smartSearchQuery = $state(data.searchParams.smartQuery || ''); // Separate AI search input that preserves original query
	let tastingNotesQuery = $state(data.searchParams.tastingNotesQuery || ''); // Separate tasting notes search input
	let roasterFilter = $state<string[]>(data.searchParams.roasterFilter || []);
	let roasterLocationFilter = $state<string[]>(data.searchParams.roasterLocationFilter || []);
	let countryFilter = $state<string[]>(data.searchParams.countryFilter || []);
	let roastLevelFilter = $state(data.searchParams.roastLevelFilter);
	let roastProfileFilter = $state(data.searchParams.roastProfileFilter);
	let processFilter = $state<string>(data.searchParams.processFilter || '');
	let varietyFilter = $state<string>(data.searchParams.varietyFilter || '');
	let minPrice = $state(data.searchParams.minPrice);
	let maxPrice = $state(data.searchParams.maxPrice);
	let minWeight = $state(data.searchParams.minWeight);
	let maxWeight = $state(data.searchParams.maxWeight);
	let minElevation = $state(data.searchParams.minElevation || '');
	let maxElevation = $state(data.searchParams.maxElevation || '');
	let regionFilter = $state(data.searchParams.regionFilter || '');
	let producerFilter = $state(data.searchParams.producerFilter || '');
	let farmFilter = $state(data.searchParams.farmFilter || '');
	let inStockOnly = $state(data.searchParams.inStockOnly);
	let isDecaf = $state(data.searchParams.isDecaf);
	let isSingleOrigin = $state<boolean | undefined>(data.searchParams.isSingleOrigin);
	let tastingNotesOnly = $state(data.searchParams.tastingNotesOnly || false);
	let sortBy = $state(data.searchParams.sortBy || 'scraped_at');
	let sortOrder = $state(data.searchParams.sortOrder || 'desc');
	let perPage = $state(data.searchParams.perPage);

	// Dropdown options
	let countryOptions: { value: string; text: string; }[] = $state([]);
	let allRoasters: Roaster[] = $state([]);  // Store full roaster data with location codes
	let roasterOptions: { value: string; text: string; }[] = $state([]);
	let roasterLocationOptions: { value: string; text: string; }[] = $state([]);




	// Load options when component mounts
	onMount(() => {
		loadDropdownOptions();
		checkAISearchHealth();
	});

	// AI search state
	let aiSearchLoading = $state(false);
	let aiSearchAvailable = $state(true);
	let dropdownOptionsLoaded = $state(false);

	// Load dropdown options on component mount
	async function loadDropdownOptions() {
		try {
			// Load countries
			const countriesResponse = await api.getCountries();
			if (countriesResponse.success && countriesResponse.data) {
				countryOptions = countriesResponse.data.map(country => ({
					value: country.country_code,
					text: country.country_name || country.country_code
				}));
			}
			countryFilter = data.searchParams.countryFilter || [];

			// Load all roasters with location codes
			const roastersResponse = await api.getRoasters();
			if (roastersResponse.success && roastersResponse.data) {
				allRoasters = roastersResponse.data;
				roasterOptions = roastersResponse.data.map(roaster => ({
					value: roaster.name,
					text: roaster.name
				}));
			}
			roasterFilter = data.searchParams.roasterFilter || [];
		// if (allRoasters.length > 0 && roasterLocationFilter.length > 0) {
		// 	if (filteredRoasterOptions && filteredRoasterOptions.length >= 0) {
		// 		// Get available roaster names from filtered options
		// 		const availableRoasterNames = filteredRoasterOptions.map((option: { value: string; text: string; }) => option.value);
		// 		// Remove roasters from selection that are no longer available
		// 		roasterFilter = roasterFilter.filter(roaster => availableRoasterNames.includes(roaster));
		// 	}
		// }

			// Load roaster locations
			const roasterLocationsResponse = await api.getRoasterLocations();
			if (roasterLocationsResponse.success && roasterLocationsResponse.data) {
				roasterLocationOptions = roasterLocationsResponse.data.map(location => ({
					value: location.code,
					text: `${location.code} - ${location.location} (${location.roaster_count})`
				}));
			}
			roasterLocationFilter = data.searchParams.roasterLocationFilter || [];

			// Mark dropdown options as loaded
			dropdownOptionsLoaded = true;

		} catch (error) {
			console.error('Error loading dropdown options:', error);
			dropdownOptionsLoaded = true; // Set to true even on error to avoid blocking UI
		}
	}


	// Check if AI search is available
	async function checkAISearchHealth() {
		try {
			const response = await api.aiSearchHealth();
			aiSearchAvailable = response.success;
		} catch (error) {
			console.warn('AI search service not available:', error);
			aiSearchAvailable = false;
		}
	}

			// Function to build search parameters - updated for new schema
	function buildSearchParams(page: number = 1) {
		return {
			// Send both regular query and tasting notes query if available
			query: searchQuery || undefined,
			tasting_notes_query: tastingNotesQuery || undefined,
			roaster: roasterFilter.length > 0 ? roasterFilter : undefined,
			roaster_location: roasterLocationFilter.length > 0 ? roasterLocationFilter : undefined,
			country: countryFilter.length > 0 ? countryFilter : undefined,
			region: regionFilter || undefined,
			producer: producerFilter || undefined,
			farm: farmFilter || undefined,
			roast_level: roastLevelFilter || undefined,
			roast_profile: roastProfileFilter || undefined,
			process: processFilter || undefined,
			variety: varietyFilter || undefined,
			min_price: minPrice ? parseFloat(minPrice) : undefined,
			max_price: maxPrice ? parseFloat(maxPrice) : undefined,
			min_weight: minWeight ? parseInt(minWeight) : undefined,
			max_weight: maxWeight ? parseInt(maxWeight) : undefined,
			min_elevation: minElevation ? parseInt(minElevation) : undefined,
			max_elevation: maxElevation ? parseInt(maxElevation) : undefined,
			in_stock_only: inStockOnly,
			is_decaf: isDecaf,
			is_single_origin: isSingleOrigin,
			page: page,
			per_page: perPage,
			sort_by: sortBy,
			sort_order: sortOrder
		};
	}

	// Load more results for infinite scroll
	const loadMore = async () => {
		try {
			pageNumber += 1;

			// If there are less results on the first page than the limit,
			// don't keep trying to fetch more. We're done.
			if (allResults.length < perPage) {
				loaderState.complete();
				return;
			}

			const params = buildSearchParams(pageNumber);
			const response = await api.search(params);

			if (!response.success) {
				loaderState.error();
				pageNumber -= 1;
				return;
			}

			if (response.data && response.data.length > 0) {
				allResults.push(...response.data);
			}

			// Update total results
			totalResults = response.pagination?.total_items || totalResults;

			// Check if we've loaded all available results
			if (allResults.length >= totalResults || (response.data && response.data.length < perPage)) {
				loaderState.complete();
			} else {
				loaderState.loaded();
			}
		} catch (err) {
			console.error('Error loading more results:', err);
			loaderState.error();
			pageNumber -= 1;
		}
	};

	// Perform new search (reset results)
	async function performNewSearch() {
		try {
			pageNumber = 1;
			loaderState.reset();

			const params = buildSearchParams(1);
			const response = await api.search(params);

			if (response.success && response.data) {
				allResults = response.data;
				totalResults = response.pagination?.total_items || 0;

				// Set initial loader state
				if (response.data.length === 0) {
					loaderState.complete();
				} else if (allResults.length >= totalResults || response.data.length < perPage) {
					loaderState.complete();
				} else {
					loaderState.loaded();
				}
			} else {
				error = response.message || 'Search failed';
				allResults = [];
				totalResults = 0;
				loaderState.error();
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'An error occurred';
			allResults = [];
			totalResults = 0;
			loaderState.error();
		}

		updateURL();
	}

	function updateURL() {
		const params = new URLSearchParams();
		if (searchQuery) params.set('q', searchQuery);
		if (tastingNotesQuery) params.set('tasting_notes_query', tastingNotesQuery);
		if (smartSearchQuery) params.set('smart_query', smartSearchQuery);
		if (roasterFilter.length > 0) {
			roasterFilter.forEach(r => params.append('roaster', r));
		}
		if (roasterLocationFilter.length > 0) {
			roasterLocationFilter.forEach(rl => params.append('roaster_location', rl));
		}
		if (countryFilter.length > 0) {
			countryFilter.forEach(c => params.append('country', c));
		}
		if (regionFilter) {
			params.set('region', regionFilter);
		}
		if (producerFilter) {
			params.set('producer', producerFilter);
		}
		if (farmFilter) {
			params.set('farm', farmFilter);
		}
		if (roastLevelFilter) params.set('roast_level', roastLevelFilter);
		if (roastProfileFilter) params.set('roast_profile', roastProfileFilter);
		if (processFilter) params.set('process', processFilter);
		if (varietyFilter) params.set('variety', varietyFilter);
		if (minPrice) params.set('min_price', minPrice);
		if (maxPrice) params.set('max_price', maxPrice);
		if (minWeight) params.set('min_weight', minWeight);
		if (maxWeight) params.set('max_weight', maxWeight);
		if (minElevation) params.set('min_elevation', minElevation);
		if (maxElevation) params.set('max_elevation', maxElevation);
		if (inStockOnly) params.set('in_stock_only', 'true');
		if (isDecaf !== undefined && isDecaf !== null) params.set('is_decaf', isDecaf.toString());
		if (isSingleOrigin !== undefined && isSingleOrigin !== null) params.set('is_single_origin', isSingleOrigin.toString());
		if (sortBy !== 'name') params.set('sort_by', sortBy);
		if (sortOrder !== 'asc') params.set('sort_order', sortOrder);

		const newUrl = `/search${params.toString() ? '?' + params.toString() : ''}`;
		goto(newUrl, { replaceState: true });
	}

	function clearFilters() {
		searchQuery = '';
		smartSearchQuery = '';
		tastingNotesQuery = '';
		roasterFilter = [];
		roasterLocationFilter = [];
		countryFilter = [];
		regionFilter = '';
		producerFilter = '';
		farmFilter = '';
		roastLevelFilter = '';
		roastProfileFilter = '';
		processFilter = '';
		varietyFilter = '';
		minPrice = '';
		maxPrice = '';
		minWeight = '';
		maxWeight = '';
		minElevation = '';
		maxElevation = '';
		inStockOnly = false;
		isDecaf = undefined;
		isSingleOrigin = undefined;
		tastingNotesOnly = false;
		sortBy = 'name';
		sortOrder = 'asc';
		// Filtered roaster options will automatically update via $derived
		performNewSearch();
	}

	// Check if any filters are applied
	const hasFiltersApplied = $derived(
		!!(searchQuery || tastingNotesQuery || roasterFilter.length > 0 ||
		roasterLocationFilter.length > 0 || countryFilter.length > 0 ||
		regionFilter || producerFilter || farmFilter || roastLevelFilter ||
		roastProfileFilter || processFilter.length > 0 || varietyFilter.length > 0 ||
		minPrice || maxPrice || minWeight || maxWeight || minElevation ||
		maxElevation || inStockOnly || isDecaf || isSingleOrigin || tastingNotesOnly)
	);

	// AI Search functionality
	async function performAISearch() {
		if (!smartSearchQuery || !aiSearchAvailable) return;

		try {
			aiSearchLoading = true;
			error = '';

			// Ensure dropdown options are loaded before applying AI search results
			if (!dropdownOptionsLoaded) {
				await loadDropdownOptions();
			}

			// Use the AI search to get parsed parameters
			const aiResult = await api.aiSearchParameters(smartSearchQuery);

			if (aiResult.success && aiResult.searchParams) {
				// Apply AI-generated search parameters to the form
				const params = aiResult.searchParams;

				// Clear all existing filters first, then apply only AI-generated ones
				// This ensures we don't mix old manual filters with new AI results

				// Update search queries (preserve the original AI query, apply AI-parsed queries)
				searchQuery = params.query || '';
				tastingNotesQuery = params.tasting_notes_query || '';

				// Apply all AI-generated filters (clear if not provided by AI)
				roasterFilter = Array.isArray(params.roaster) ? params.roaster : (params.roaster ? [params.roaster] : []);
				roasterLocationFilter = Array.isArray(params.roaster_location) ? params.roaster_location : (params.roaster_location ? [params.roaster_location] : []);
				countryFilter = Array.isArray(params.country) ? params.country : (params.country ? [params.country] : []);
				regionFilter = params.region || '';
				producerFilter = params.producer || '';
				farmFilter = params.farm || '';
				roastLevelFilter = params.roast_level || '';
				roastProfileFilter = params.roast_profile || '';
				processFilter = params.process || '';
				varietyFilter = params.variety || '';
				minPrice = params.min_price?.toString() || '';
				maxPrice = params.max_price?.toString() || '';
				minWeight = params.min_weight?.toString() || '';
				maxWeight = params.max_weight?.toString() || '';
				minElevation = params.min_elevation?.toString() || '';
				maxElevation = params.max_elevation?.toString() || '';
				inStockOnly = params.in_stock_only || false;
				isDecaf = params.is_decaf ?? undefined;
				isSingleOrigin = params.is_single_origin ?? undefined;
				sortBy = params.sort_by || 'name';
				sortOrder = params.sort_order || 'asc';

				// Perform the search with the AI-generated parameters
				await performNewSearch();
			} else {
				// AI search failed, fall back to regular search
				error = aiResult.error || 'AI search failed';
				await performNewSearch();
			}

		} catch (err) {
			console.error('AI search error:', err);
			error = err instanceof Error ? err.message : 'AI search failed';
			// Fall back to regular search
			performNewSearch();
		} finally {
			aiSearchLoading = false;
		}
	}

</script>

<svelte:head>
	<title>Search Coffee Beans - Kissaten</title>
	<meta name="description" content="Search and discover coffee beans from roasters worldwide" />
</svelte:head>

<div class="mx-auto px-4 py-8 container">
	<div class="flex lg:flex-row flex-col gap-2 lg:gap-8">
		<!-- Mobile title -->
		<h1 class="lg:hidden block mb-4 font-bold text-3xl">Coffee Beans</h1>

		<!-- Desktop Sidebar Filters -->
		<div class="hidden lg:block">
			<SearchFilters
				bind:searchQuery
				bind:tastingNotesQuery
				bind:roasterFilter
				bind:roasterLocationFilter
				bind:countryFilter
				bind:roastLevelFilter
				bind:roastProfileFilter
				bind:processFilter
				bind:varietyFilter
				bind:minPrice
				bind:maxPrice
				bind:minWeight
				bind:maxWeight
				bind:minElevation
				bind:maxElevation
				bind:regionFilter
				bind:producerFilter
				bind:farmFilter
				bind:inStockOnly
				bind:isDecaf
				bind:isSingleOrigin
				bind:sortBy
				bind:sortOrder
				bind:showFilters
				{countryOptions}
				{allRoasters}
				{roasterLocationOptions}
				onSearch={performNewSearch}
				onClearFilters={clearFilters}
			/>
		</div>

		<!-- Search Results with mobile integrated filters -->
		<SearchResults
			results={allResults}
			{totalResults}
			{loaderState}
			{error}
			{hasFiltersApplied}
			onLoadMore={loadMore}
			onClearFilters={clearFilters}
			onRetrySearch={performNewSearch}
			bind:aiSearchValue={smartSearchQuery}
			{aiSearchLoading}
			{aiSearchAvailable}
			onAISearch={performAISearch}
			bind:searchQuery
			bind:tastingNotesQuery
			bind:roasterFilter
			bind:roasterLocationFilter
			bind:countryFilter
			bind:roastLevelFilter
			bind:roastProfileFilter
			bind:processFilter
			bind:varietyFilter
			bind:minPrice
			bind:maxPrice
			bind:minWeight
			bind:maxWeight
			bind:minElevation
			bind:maxElevation
			bind:regionFilter
			bind:producerFilter
			bind:farmFilter
			bind:inStockOnly
			bind:isDecaf
			bind:isSingleOrigin
			bind:sortBy
			bind:sortOrder
			bind:showFilters
			{countryOptions}
			{allRoasters}
			{roasterLocationOptions}
			onSearch={performNewSearch}
		/>
	</div>
</div>

