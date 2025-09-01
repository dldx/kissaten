<script lang="ts">
	import { goto } from '$app/navigation';
	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
	import { InfiniteLoader, LoaderState } from "$lib/components/infinite-scroll";
	import { Search, Filter, Coffee, MapPin, DollarSign, Weight, Package, Sparkles, Loader2 } from "lucide-svelte";
	import { api, type CoffeeBean, type APIResponse, type Country, type RoasterLocation, type Roaster } from '$lib/api.js';
	import type { PageData } from './$types';
	import Svelecte from 'svelecte';
    import { onMount } from 'svelte';

	interface Props {
		data: PageData;
	}

	interface CountryOption {
		value: string;
		text: string;
	}

	interface RoasterLocationOption {
		value: string;
		text: string;
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
	let aiSearchQuery = $state(''); // Separate AI search input that preserves original query
	let tastingNotesQuery = $state(data.searchParams.tastingNotesQuery || ''); // Separate tasting notes search input
	let roasterFilter = $state<string[]>(data.searchParams.roasterFilter || []);
	let roasterLocationFilter = $state<string[]>(data.searchParams.roasterLocationFilter || []);
	let countryFilter = $state<string[]>(data.searchParams.countryFilter || []);
	let roastLevelFilter = $state(data.searchParams.roastLevelFilter);
	let roastProfileFilter = $state(data.searchParams.roastProfileFilter);
	let processFilter = $state<string>(data.searchParams.processFilter?.join(', ') || '');
	let varietyFilter = $state<string>(data.searchParams.varietyFilter?.join(', ') || '');
	let minPrice = $state(data.searchParams.minPrice);
	let maxPrice = $state(data.searchParams.maxPrice);
	let minWeight = $state(data.searchParams.minWeight);
	let maxWeight = $state(data.searchParams.maxWeight);
	let minElevation = $state(data.searchParams.minElevation || '');
	let maxElevation = $state(data.searchParams.maxElevation || '');
	let regionFilter = $state(data.searchParams.regionFilter?.join(', ') || '');
	let producerFilter = $state(data.searchParams.producerFilter?.join(', ') || '');
	let farmFilter = $state(data.searchParams.farmFilter?.join(', ') || '');
	let inStockOnly = $state(data.searchParams.inStockOnly);
	let isDecaf = $state(data.searchParams.isDecaf);
	let isSingleOrigin = $state<boolean | undefined>(data.searchParams.isSingleOrigin);
	let tastingNotesOnly = $state(data.searchParams.tastingNotesOnly || false);
	let sortBy = $state(data.searchParams.sortBy || 'scraped_at');
	let sortOrder = $state(data.searchParams.sortOrder || 'desc');
	let perPage = $state(data.searchParams.perPage);

	// Dropdown options
	let countryOptions: CountryOption[] = $state([]);
	let allRoasters: Roaster[] = $state([]);  // Store full roaster data with location codes
	let roasterOptions: { value: string; text: string; }[] = $state([]);
	let roasterLocationOptions: RoasterLocationOption[] = $state([]);

	// Option resolver for roaster filtering based on location selection
	const filteredRoasterOptions: { value: string; text: string; }[] = $derived.by(() => {
			// Show filtered roasters based on location selection
			if (!allRoasters || allRoasters.length === 0) {
				return [];
			}
			if (roasterLocationFilter.length === 0) {
				return allRoasters.map(roaster => ({
					value: roaster.name,
					text: roaster.name
				}));
			}

			const filteredRoasters = allRoasters.filter(roaster => {
				return roaster.location_codes && roasterLocationFilter.some(locationCode =>
					roaster.location_codes.includes(locationCode.toUpperCase())
				);
			});

			return filteredRoasters.map(roaster => ({
				value: roaster.name,
				text: roaster.name
			}));
		});


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
			region: regionFilter ? [regionFilter] : undefined,
			producer: producerFilter ? [producerFilter] : undefined,
			farm: farmFilter ? [farmFilter] : undefined,
			roast_level: roastLevelFilter || undefined,
			roast_profile: roastProfileFilter || undefined,
			process: processFilter ? processFilter.split(',').map(p => p.trim()).filter(p => p) : undefined,
			variety: varietyFilter ? varietyFilter.split(',').map(v => v.trim()).filter(v => v) : undefined,
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
		if (processFilter) {
			processFilter.split(',').map(p => p.trim()).filter(p => p).forEach(p => params.append('process', p));
		}
		if (varietyFilter) {
			varietyFilter.split(',').map(v => v.trim()).filter(v => v).forEach(v => params.append('variety', v));
		}
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
		aiSearchQuery = '';
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

	// AI Search functionality
	async function performAISearch() {
		if (!aiSearchQuery || !aiSearchAvailable) return;

		try {
			aiSearchLoading = true;
			error = '';

			// Ensure dropdown options are loaded before applying AI search results
			if (!dropdownOptionsLoaded) {
				await loadDropdownOptions();
			}

			// Use the AI search to get parsed parameters
			const aiResult = await api.aiSearchParameters(aiSearchQuery);

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
				regionFilter = Array.isArray(params.region) ? params.region.join(', ') : (params.region || '');
				producerFilter = Array.isArray(params.producer) ? params.producer.join(', ') : (params.producer || '');
				farmFilter = Array.isArray(params.farm) ? params.farm.join(', ') : (params.farm || '');
				roastLevelFilter = params.roast_level || '';
				roastProfileFilter = params.roast_profile || '';
				processFilter = Array.isArray(params.process) ? params.process.join(', ') : (params.process || '');
				varietyFilter = Array.isArray(params.variety) ? params.variety.join(', ') : (params.variety || '');
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
	<div class="flex lg:flex-row flex-col gap-8">
		<!-- Filters Sidebar -->
		<aside class="space-y-6 lg:w-80">
			<div class="flex justify-between items-center">
				<h2 class="font-bold text-2xl">Filters</h2>
				<Button variant="ghost" size="sm" onclick={() => showFilters = !showFilters} class="lg:hidden">
					<Filter class="w-4 h-4" />
				</Button>
			</div>

			<div class="space-y-4" class:hidden={!showFilters} class:lg:block={true}>
					<Button variant="outline" class="w-full" onclick={clearFilters}>
						Clear All
					</Button>
				<!-- AI Search -->
				{#if aiSearchAvailable}
					<div>
						<label class="block mb-2 font-medium text-sm">AI Search</label>
						<div class="relative">
							<Sparkles class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
							<Input
								bind:value={aiSearchQuery}
								placeholder="Describe what you're looking for..."
								class="pl-10"
								onkeypress={(e: KeyboardEvent) => {
									if (e.key === 'Enter') {
										performAISearch();
									}
								}}
							/>
						</div>
						{#if aiSearchQuery}
							<div class="mt-2">
								<Button
									variant="outline"
									size="sm"
									onclick={performAISearch}
									disabled={aiSearchLoading || !aiSearchQuery.trim()}
									class="w-full text-xs"
								>
									{#if aiSearchLoading}
										<Loader2 class="mr-2 w-3 h-3 animate-spin" />
										AI Processing...
									{:else}
										<Sparkles class="mr-2 w-3 h-3" />
										Translate to Filters
									{/if}
								</Button>
								<p class="mt-1 text-muted-foreground text-xs">
									Let AI interpret your search and set filters
								</p>
							</div>
						{/if}
					</div>
				{/if}

				<!-- Regular Search Query -->
				<div>
					<label class="block mb-2 font-medium text-sm">Search</label>
					<div class="relative">
						<Search class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
						<Input
							bind:value={searchQuery}
							placeholder="Bean names, roasters, origins..."
							class="pl-10"
							onkeypress={(e: KeyboardEvent) => {
								if (e.key === 'Enter') {
									performNewSearch();
								}
							}}
						/>
					</div>
				</div>

				<!-- Tasting Notes Search -->
				<div>
					<label class="block mb-2 font-medium text-sm">Tasting Notes Search</label>
					<div class="relative">
						<Coffee class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
						<Input
							bind:value={tastingNotesQuery}
							placeholder="chocolate|caramel, berry&!bitter..."
							class="pl-10"
							onkeypress={(e: KeyboardEvent) => {
								if (e.key === 'Enter') {
									performNewSearch();
								}
							}}
						/>
					</div>
					{#if tastingNotesQuery}
						<div class="bg-muted/50 mt-2 px-3 py-2 rounded-md text-muted-foreground text-xs">
							<p class="mb-1"><strong>Advanced search syntax:</strong></p>
							<p class="mb-1">• Use <code>|</code> for OR: <code>chocolate|caramel</code></p>
							<p class="mb-1">• Use <code>&</code> for AND: <code>sweet&fruit*</code></p>
							<p class="mb-1">• Use <code>!</code> for NOT: <code>chocolate&!bitter</code></p>
							<p class="mb-1">• Use <code>*</code> and <code>?</code> for wildcards</p>
							<p>• Use <code>()</code> for grouping: <code>berry&(lemon|lime)</code></p>
						</div>
					{/if}
				</div>

				<!-- Roaster Location Filter -->
				<div>
					<label class="block mb-2 font-medium text-sm">Roaster Location</label>
					<Svelecte
						bind:value={roasterLocationFilter}
						options={roasterLocationOptions || []}
						placeholder="Filter by roaster location..."
						searchable
						clearable
						multiple
						class="w-full"
						onChange={() => {
							// Client-side filtering is immediate, no need for setTimeout
							performNewSearch();
						}}
					/>
				</div>

				<!-- Roaster Filter -->
				<div>
					<label class="block mb-2 font-medium text-sm">Roaster</label>
					{#key filteredRoasterOptions}
					<Svelecte
						bind:value={roasterFilter}
						options={filteredRoasterOptions}
						placeholder={roasterLocationFilter.length > 0
							? `Filter roasters in ${roasterLocationFilter.join(', ')}...`
							: "Filter by roaster..."}
						searchable
						clearable
						multiple
						class="w-full"
						onChange={() => performNewSearch()}
					/>
					{/key}
					{#if roasterLocationFilter.length > 0}
						{@const currentFilteredOptions = filteredRoasterOptions}
						{#if currentFilteredOptions.length > 0}
							<p class="mt-1 text-muted-foreground text-xs">
								Showing {currentFilteredOptions.length} roasters in selected location{roasterLocationFilter.length > 1 ? 's' : ''}
							</p>
						{/if}
					{/if}
				</div>

				<!-- Country Filter -->
				<div>
					<label class="block mb-2 font-medium text-sm">Country</label>
					<Svelecte
						bind:value={countryFilter}
						options={countryOptions || []}
						placeholder="Filter by origin country..."
						searchable
						clearable
						multiple
						class="w-full"
						onChange={() => performNewSearch()}
					/>
				</div>

				<!-- Region Filter -->
				<div>
					<label class="block mb-2 font-medium text-sm">Region</label>
					<Input
						bind:value={regionFilter}
						placeholder="Antioquia, Huila, Yirgacheffe..."
						onkeypress={(e: KeyboardEvent) => {
							if (e.key === 'Enter') {
								performNewSearch();
							}
						}}
					/>
				</div>

				<!-- Producer Filter -->
				<div>
					<label class="block mb-2 font-medium text-sm">Producer</label>
					<Input
						bind:value={producerFilter}
						placeholder="Producer name..."
						onkeypress={(e: KeyboardEvent) => {
							if (e.key === 'Enter') {
								performNewSearch();
							}
						}}
					/>
				</div>

				<!-- Farm Filter -->
				<div>
					<label class="block mb-2 font-medium text-sm">Farm</label>
					<Input
						bind:value={farmFilter}
						placeholder="Farm name..."
						onkeypress={(e: KeyboardEvent) => {
							if (e.key === 'Enter') {
								performNewSearch();
							}
						}}
					/>
				</div>

				<!-- Roast Level Filter -->
				<div>
					<label class="block mb-2 font-medium text-sm">Roast Level</label>
					<Input
						bind:value={roastLevelFilter}
						placeholder="Light, Medium, Dark..."
						onkeypress={(e: KeyboardEvent) => {
							if (e.key === 'Enter') {
								performNewSearch();
							}
						}}
					/>
				</div>

				<!-- Roast Profile Filter -->
				<div>
					<label class="block mb-2 font-medium text-sm">Roast Profile</label>
					<Input
						bind:value={roastProfileFilter}
						placeholder="Espresso, Filter..."
						onkeypress={(e: KeyboardEvent) => {
							if (e.key === 'Enter') {
								performNewSearch();
							}
						}}
					/>
				</div>

				<!-- Process Filter -->
				<div>
					<label class="block mb-2 font-medium text-sm">Process</label>
					<Input
						bind:value={processFilter}
						placeholder="Washed, Natural, Honey..."
						onkeypress={(e: KeyboardEvent) => {
							if (e.key === 'Enter') {
								performNewSearch();
							}
						}}
					/>
				</div>

				<!-- Variety Filter -->
				<div>
					<label class="block mb-2 font-medium text-sm">Variety</label>
					<Input
						bind:value={varietyFilter}
						placeholder="Catuai, Bourbon, Geisha..."
						onkeypress={(e: KeyboardEvent) => {
							if (e.key === 'Enter') {
								performNewSearch();
							}
						}}
					/>
				</div>

				<!-- Elevation Range -->
				<div>
					<label class="block mb-2 font-medium text-sm">Elevation (meters)</label>
					<div class="flex gap-2">
						<Input
							bind:value={minElevation}
							placeholder="Min"
							type="number"
							onkeypress={(e: KeyboardEvent) => {
								if (e.key === 'Enter') {
									performNewSearch();
								}
							}}
						/>
						<Input
							bind:value={maxElevation}
							placeholder="Max"
							type="number"
							onkeypress={(e: KeyboardEvent) => {
								if (e.key === 'Enter') {
									performNewSearch();
								}
							}}
						/>
					</div>
				</div>

				<!-- Price Range -->
				<div>
					<label class="block mb-2 font-medium text-sm">Price Range</label>
					<div class="flex gap-2">
						<Input
							bind:value={minPrice}
							placeholder="Min"
							type="number"
							step="0.01"
							onkeypress={(e: KeyboardEvent) => {
								if (e.key === 'Enter') {
									performNewSearch();
								}
							}}
						/>
						<Input
							bind:value={maxPrice}
							placeholder="Max"
							type="number"
							step="0.01"
							onkeypress={(e: KeyboardEvent) => {
								if (e.key === 'Enter') {
									performNewSearch();
								}
							}}
						/>
					</div>
				</div>

				<!-- Weight Range -->
				<div>
					<label class="block mb-2 font-medium text-sm">Weight (grams)</label>
					<div class="flex gap-2">
						<Input
							bind:value={minWeight}
							placeholder="Min"
							type="number"
							onkeypress={(e: KeyboardEvent) => {
								if (e.key === 'Enter') {
									performNewSearch();
								}
							}}
						/>
						<Input
							bind:value={maxWeight}
							placeholder="Max"
							type="number"
							onkeypress={(e: KeyboardEvent) => {
								if (e.key === 'Enter') {
									performNewSearch();
								}
							}}
						/>
					</div>
				</div>

				<!-- In Stock Only -->
				<div class="flex items-center space-x-2">
					<input
						type="checkbox"
						id="inStock"
						bind:checked={inStockOnly}
						onchange={() => performNewSearch()}
						class="border-input rounded"
					/>
					<label for="inStock" class="font-medium text-sm">In stock only</label>
				</div>

				<!-- Decaf Filter -->
				<div class="space-y-2">
					<label class="block font-medium text-sm">Decaf</label>
					<div class="flex items-center space-x-4">
						<div class="flex items-center space-x-2">
							<input
								type="radio"
								id="decaf-all"
								name="decaf"
								value=""
								checked={isDecaf === undefined}
								onchange={() => {
									isDecaf = undefined;
									performNewSearch();
								}}
								class="border-input"
							/>
							<label for="decaf-all" class="text-sm">All</label>
						</div>
						<div class="flex items-center space-x-2">
							<input
								type="radio"
								id="decaf-yes"
								name="decaf"
								value="true"
								checked={isDecaf === true}
								onchange={() => {
									isDecaf = true;
									performNewSearch();
								}}
								class="border-input"
							/>
							<label for="decaf-yes" class="text-sm">Decaf only</label>
						</div>
						<div class="flex items-center space-x-2">
							<input
								type="radio"
								id="decaf-no"
								name="decaf"
								value="false"
								checked={isDecaf === false}
								onchange={() => {
									isDecaf = false;
									performNewSearch();
								}}
								class="border-input"
							/>
							<label for="decaf-no" class="text-sm">Regular only</label>
						</div>
					</div>
				</div>

				<!-- Single Origin vs Blend Filter -->
				<div class="space-y-2">
					<label class="block font-medium text-sm">Origin Type</label>
					<div class="flex items-center space-x-4">
						<div class="flex items-center space-x-2">
							<input
								type="radio"
								id="origin-all"
								name="origin-type"
								value=""
								checked={isSingleOrigin === undefined}
								onchange={() => {
									isSingleOrigin = undefined;
									performNewSearch();
								}}
								class="border-input"
							/>
							<label for="origin-all" class="text-sm">All</label>
						</div>
						<div class="flex items-center space-x-2">
							<input
								type="radio"
								id="origin-single"
								name="origin-type"
								value="true"
								checked={isSingleOrigin === true}
								onchange={() => {
									isSingleOrigin = true;
									performNewSearch();
								}}
								class="border-input"
							/>
							<label for="origin-single" class="text-sm">Single Origin</label>
						</div>
						<div class="flex items-center space-x-2">
							<input
								type="radio"
								id="origin-blend"
								name="origin-type"
								value="false"
								checked={isSingleOrigin === false}
								onchange={() => {
									isSingleOrigin = false;
									performNewSearch();
								}}
								class="border-input"
							/>
							<label for="origin-blend" class="text-sm">Blends</label>
						</div>
					</div>
				</div>



				<!-- Sort Options -->
				<div>
					<label class="block mb-2 font-medium text-sm">Sort by</label>
					<select bind:value={sortBy} onchange={() => performNewSearch()} class="bg-background px-3 py-2 border border-input rounded-md w-full text-sm">
						<option value="name">Name</option>
						<option value="roaster">Roaster</option>
						<option value="price">Price</option>
						<option value="weight">Weight</option>
						<option value="country">Country</option>
						<option value="region">Region</option>
						<option value="elevation">Elevation</option>
						<option value="variety">Variety</option>
						<option value="process">Process</option>
						<option value="cupping_score">Cupping Score</option>
						<option value="scraped_at">Date Added</option>
					</select>
					<select bind:value={sortOrder} onchange={() => performNewSearch()} class="bg-background mt-2 px-3 py-2 border border-input rounded-md w-full text-sm">
						<option value="asc">Ascending</option>
						<option value="desc">Descending</option>
					</select>
				</div>

				<!-- Action Buttons -->
				<div class="space-y-2">
					<Button class="w-full" onclick={() => performNewSearch()}>
						<Search class="mr-2 w-4 h-4" />
						Apply Filters
					</Button>
					<Button variant="outline" class="w-full" onclick={clearFilters}>
						Clear All
					</Button>
				</div>
			</div>
		</aside>

		<!-- Results -->
		<main class="flex-1">
			<!-- Results Header -->
			<div class="flex justify-between items-center mb-6">
				<div>
					<h1 class="font-bold text-3xl">Coffee Beans</h1>
					<p class="text-muted-foreground">
						{#if allResults.length === totalResults}
							{totalResults} results found
						{:else}
							Showing {allResults.length} of {totalResults} results
						{/if}
						{#if searchQuery || tastingNotesQuery}
							for
							{#if searchQuery && tastingNotesQuery}
								"{searchQuery}" + tasting notes "{tastingNotesQuery}"
							{:else if searchQuery}
								"{searchQuery}"
							{:else if tastingNotesQuery}
								tasting notes "{tastingNotesQuery}"
							{/if}
						{/if}
					</p>
				</div>
			</div>

			<!-- Error State -->
			{#if error}
				<div class="py-12 text-center">
					<p class="mb-4 text-red-500">{error}</p>
					<Button onclick={() => performNewSearch()}>Try Again</Button>
				</div>
			{:else}
				<!-- Infinite Scroll Results -->
				<InfiniteLoader
					{loaderState}
					triggerLoad={loadMore}
					intersectionOptions={{ rootMargin: "0px 0px 200px 0px" }}
				>
					<div class="gap-6 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 mb-8">
						{#each allResults as bean (bean.id)}
							<a href={"/roasters" + bean.bean_url_path} class="block">
								<CoffeeBeanCard {bean} class="h-full" />
							</a>
						{/each}
					</div>

					{#snippet loading()}
						<div class="flex flex-col items-center space-y-4">
							<div class="inline-block border-primary border-b-2 rounded-full w-6 h-6 animate-spin"></div>
							<p class="text-muted-foreground text-sm">Loading more beans...</p>
						</div>
					{/snippet}

					{#snippet noResults()}
						<div class="py-12 text-center">
							<Coffee class="mx-auto mb-4 w-12 h-12 text-muted-foreground" />
							<h3 class="mb-2 font-semibold text-xl">No coffee beans found</h3>
							<p class="mb-4 text-muted-foreground">Try adjusting your search criteria or clearing some filters.</p>
							<Button onclick={clearFilters}>Clear Filters</Button>
						</div>
					{/snippet}

					{#snippet noData()}
						<div class="py-8 text-center">
							<p class="text-muted-foreground">You've reached the end of the results!</p>
						</div>
					{/snippet}

					{#snippet error(retryFn)}
						<div class="py-12 text-center">
							<p class="mb-4 text-red-500">Failed to load more results</p>
							<Button onclick={retryFn}>Try Again</Button>
						</div>
					{/snippet}
				</InfiniteLoader>
			{/if}
		</main>
	</div>
</div>

<style>
	/* Svelecte custom styling to match the design */
	:global(.svelecte) {
		--sv-border: 1px solid var(--border);
		--sv-border-radius: calc(var(--radius) - 2px);
		--sv-bg: var(--background);
		--sv-control-bg: var(--background);
		--sv-color: var(--foreground);
		--sv-placeholder-color: var(--muted-foreground);
		--sv-min-height: 2.5rem;
		--sv-font-size: 0.875rem;
	}

	:global(.svelecte:focus-within) {
		--sv-border: 2px solid hsl(var(--ring));
	}

	:global(.svelecte .sv-dropdown) {
		--sv-dropdown-bg: var(--popover);
		--sv-dropdown-border: 1px solid var(--border);
		--sv-dropdown-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
		--sv-dropdown-active-bg: var(--accent);
		--sv-dropdown-selected-bg: var(--primary);
	}

	:global(.svelecte .sv-item:hover) {
		--sv-dropdown-active-bg: var(--accent);
	}

	:global(.svelecte .sv-item.is-selected) {
		--sv-dropdown-selected-bg: var(--primary);
		color: var(--primary-foreground);
	}

	/* Styling for multiple selection chips */
	:global(.svelecte.is-multiple .sv-control) {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem;
		padding: 0.25rem;
	}

	:global(.svelecte.is-multiple .sv-item-chip) {
		background: hsl(var(--primary));
		color: hsl(var(--primary-foreground));
		padding: 0.125rem 0.5rem;
		border-radius: calc(var(--radius) - 4px);
		font-size: 0.75rem;
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	:global(.svelecte.is-multiple .sv-item-chip .sv-chip-remove) {
		cursor: pointer;
		opacity: 0.7;
	}

	:global(.svelecte.is-multiple .sv-item-chip .sv-chip-remove:hover) {
		opacity: 1;
	}
</style>