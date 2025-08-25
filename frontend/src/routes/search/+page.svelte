<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "$lib/components/ui/card/index.js";
	import { Search, Filter, Coffee, MapPin, DollarSign, Weight, Package } from "lucide-svelte";
	import { api, type CoffeeBean, type APIResponse } from '$lib/api.js';

	let searchQuery = $state('');
	let roasterFilter = $state('');
	let countryFilter = $state('');
	let roastLevelFilter = $state('');
	let processFilter = $state('');
	let varietyFilter = $state('');
	let minPrice = $state('');
	let maxPrice = $state('');
	let minWeight = $state('');
	let maxWeight = $state('');
	let inStockOnly = $state(false);
	let sortBy = $state('name');
	let sortOrder = $state('asc');
	let currentPage = $state(1);
	let perPage = $state(20);

	let searchResults: CoffeeBean[] = $state([]);
	let loading = $state(false);
	let error = $state('');
	let totalResults = $state(0);
	let totalPages = $state(0);
	let showFilters = $state(false);

	// Initialize from URL parameters
	onMount(() => {
		const urlParams = new URLSearchParams($page.url.search);
		searchQuery = urlParams.get('q') || '';
		roasterFilter = urlParams.get('roaster') || '';
		countryFilter = urlParams.get('country') || '';
		roastLevelFilter = urlParams.get('roast_level') || '';
		processFilter = urlParams.get('process') || '';
		varietyFilter = urlParams.get('variety') || '';
		minPrice = urlParams.get('min_price') || '';
		maxPrice = urlParams.get('max_price') || '';
		minWeight = urlParams.get('min_weight') || '';
		maxWeight = urlParams.get('max_weight') || '';
		inStockOnly = urlParams.get('in_stock_only') === 'true';
		sortBy = urlParams.get('sort_by') || 'name';
		sortOrder = urlParams.get('sort_order') || 'asc';
		currentPage = parseInt(urlParams.get('page') || '1');

		performSearch();
	});

	async function performSearch() {
		loading = true;
		error = '';

		try {
			const params = {
				query: searchQuery || undefined,
				roaster: roasterFilter || undefined,
				country: countryFilter || undefined,
				roast_level: roastLevelFilter || undefined,
				process: processFilter || undefined,
				variety: varietyFilter || undefined,
				min_price: minPrice ? parseFloat(minPrice) : undefined,
				max_price: maxPrice ? parseFloat(maxPrice) : undefined,
				min_weight: minWeight ? parseInt(minWeight) : undefined,
				max_weight: maxWeight ? parseInt(maxWeight) : undefined,
				in_stock_only: inStockOnly,
				page: currentPage,
				per_page: perPage,
				sort_by: sortBy,
				sort_order: sortOrder
			};

			const response = await api.search(params);

			if (response.success && response.data) {
				searchResults = response.data;
				totalResults = response.pagination?.total_items || 0;
				totalPages = response.pagination?.total_pages || 0;
			} else {
				error = response.message || 'Search failed';
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'An error occurred';
		} finally {
			loading = false;
		}

		updateURL();
	}

	function updateURL() {
		const params = new URLSearchParams();
		if (searchQuery) params.set('q', searchQuery);
		if (roasterFilter) params.set('roaster', roasterFilter);
		if (countryFilter) params.set('country', countryFilter);
		if (roastLevelFilter) params.set('roast_level', roastLevelFilter);
		if (processFilter) params.set('process', processFilter);
		if (varietyFilter) params.set('variety', varietyFilter);
		if (minPrice) params.set('min_price', minPrice);
		if (maxPrice) params.set('max_price', maxPrice);
		if (minWeight) params.set('min_weight', minWeight);
		if (maxWeight) params.set('max_weight', maxWeight);
		if (inStockOnly) params.set('in_stock_only', 'true');
		if (sortBy !== 'name') params.set('sort_by', sortBy);
		if (sortOrder !== 'asc') params.set('sort_order', sortOrder);
		if (currentPage !== 1) params.set('page', currentPage.toString());

		const newUrl = `/search${params.toString() ? '?' + params.toString() : ''}`;
		goto(newUrl, { replaceState: true });
	}

	function clearFilters() {
		searchQuery = '';
		roasterFilter = '';
		countryFilter = '';
		roastLevelFilter = '';
		processFilter = '';
		varietyFilter = '';
		minPrice = '';
		maxPrice = '';
		minWeight = '';
		maxWeight = '';
		inStockOnly = false;
		sortBy = 'name';
		sortOrder = 'asc';
		currentPage = 1;
		performSearch();
	}

	function changePage(page: number) {
		currentPage = page;
		performSearch();
	}

	function formatPrice(price: number | null, currency: string): string {
		if (price === null) return 'N/A';
		return new Intl.NumberFormat('en-US', {
			style: 'currency',
			currency: currency || 'EUR'
		}).format(price);
	}

	function createSlug(text: string): string {
		return text.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
	}

	function getBeanUrl(bean: CoffeeBean): string {
		if (bean.filename) {
			// Extract roaster and filename from the full path
			// Example: /path/to/data/roasters/roaster_name/timestamp/filename.json
			const pathParts = bean.filename.split('/');
			const roasterDir = pathParts[pathParts.length - 3]; // roaster directory
			const filename = pathParts[pathParts.length - 1].replace('.json', ''); // filename without .json
			return `/${roasterDir}/${filename}`;
		}
		// Fallback to slug-based approach
		return `/${createSlug(bean.roaster)}/${createSlug(bean.name)}`;
	}

	function getRoasterDirectoryName(roasterName: string): string {
		// Convert roaster name to directory format
		return roasterName.toLowerCase()
			.replace(/\s+/g, '_')
			.replace(/[^a-z0-9_]/g, '')
			.replace(/_{2,}/g, '_')
			.replace(/^_|_$/g, '');
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
				<!-- Search Query -->
				<div>
					<label class="block mb-2 font-medium text-sm">Search</label>
					<div class="relative">
						<Search class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
						<Input
							bind:value={searchQuery}
							placeholder="Beans, roasters, notes..."
							class="pl-10"
							onkeypress={(e: KeyboardEvent) => e.key === 'Enter' && performSearch()}
						/>
					</div>
				</div>

				<!-- Roaster Filter -->
				<div>
					<label class="block mb-2 font-medium text-sm">Roaster</label>
					<Input
						bind:value={roasterFilter}
						placeholder="Filter by roaster..."
													onkeypress={(e: KeyboardEvent) => e.key === 'Enter' && performSearch()}
					/>
				</div>

				<!-- Country Filter -->
				<div>
					<label class="block mb-2 font-medium text-sm">Country</label>
					<Input
						bind:value={countryFilter}
						placeholder="Filter by origin country..."
													onkeypress={(e: KeyboardEvent) => e.key === 'Enter' && performSearch()}
					/>
				</div>

				<!-- Roast Level Filter -->
				<div>
					<label class="block mb-2 font-medium text-sm">Roast Level</label>
					<Input
						bind:value={roastLevelFilter}
						placeholder="Light, Medium, Dark..."
													onkeypress={(e: KeyboardEvent) => e.key === 'Enter' && performSearch()}
					/>
				</div>

				<!-- Process Filter -->
				<div>
					<label class="block mb-2 font-medium text-sm">Process</label>
					<Input
						bind:value={processFilter}
						placeholder="Washed, Natural, Honey..."
													onkeypress={(e: KeyboardEvent) => e.key === 'Enter' && performSearch()}
					/>
				</div>

				<!-- Variety Filter -->
				<div>
					<label class="block mb-2 font-medium text-sm">Variety</label>
					<Input
						bind:value={varietyFilter}
						placeholder="Catuai, Bourbon, Geisha..."
													onkeypress={(e: KeyboardEvent) => e.key === 'Enter' && performSearch()}
					/>
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
							onkeypress={(e: KeyboardEvent) => e.key === 'Enter' && performSearch()}
						/>
						<Input
							bind:value={maxPrice}
							placeholder="Max"
							type="number"
							step="0.01"
							onkeypress={(e: KeyboardEvent) => e.key === 'Enter' && performSearch()}
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
							onkeypress={(e: KeyboardEvent) => e.key === 'Enter' && performSearch()}
						/>
						<Input
							bind:value={maxWeight}
							placeholder="Max"
							type="number"
							onkeypress={(e: KeyboardEvent) => e.key === 'Enter' && performSearch()}
						/>
					</div>
				</div>

				<!-- In Stock Only -->
				<div class="flex items-center space-x-2">
					<input
						type="checkbox"
						id="inStock"
						bind:checked={inStockOnly}
						onchange={performSearch}
						class="border-input rounded"
					/>
					<label for="inStock" class="font-medium text-sm">In stock only</label>
				</div>

				<!-- Sort Options -->
				<div>
					<label class="block mb-2 font-medium text-sm">Sort by</label>
					<select bind:value={sortBy} onchange={performSearch} class="bg-background px-3 py-2 border border-input rounded-md w-full text-sm">
						<option value="name">Name</option>
						<option value="roaster">Roaster</option>
						<option value="price">Price</option>
						<option value="weight">Weight</option>
						<option value="country">Country</option>
						<option value="variety">Variety</option>
						<option value="scraped_at">Date Added</option>
					</select>
					<select bind:value={sortOrder} onchange={performSearch} class="bg-background mt-2 px-3 py-2 border border-input rounded-md w-full text-sm">
						<option value="asc">Ascending</option>
						<option value="desc">Descending</option>
					</select>
				</div>

				<!-- Action Buttons -->
				<div class="space-y-2">
					<Button class="w-full" onclick={performSearch}>
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
					{#if !loading}
						<p class="text-muted-foreground">
							{totalResults} results found
							{#if searchQuery}
								for "{searchQuery}"
							{/if}
						</p>
					{/if}
				</div>
			</div>

			<!-- Loading State -->
			{#if loading}
				<div class="py-12 text-center">
					<div class="inline-block border-primary border-b-2 rounded-full w-8 h-8 animate-spin"></div>
					<p class="mt-4 text-muted-foreground">Searching...</p>
				</div>
			{/if}

			<!-- Error State -->
			{#if error}
				<div class="py-12 text-center">
					<p class="mb-4 text-red-500">{error}</p>
					<Button onclick={performSearch}>Try Again</Button>
				</div>
			{/if}

			<!-- Results Grid -->
			{#if !loading && !error && searchResults}
				<div class="gap-6 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 mb-8">
					{#each searchResults as bean (bean.id)}
						<Card class="hover:shadow-lg transition-shadow">
							<CardHeader>
								<CardTitle class="text-lg line-clamp-2">
									<a href={getBeanUrl(bean)} class="hover:text-primary transition-colors">
										{bean.name}
									</a>
								</CardTitle>
								<CardDescription class="flex items-center">
									<Coffee class="mr-1 w-4 h-4" />
									{bean.roaster}
								</CardDescription>
							</CardHeader>
							<CardContent>
								<div class="space-y-3">
									{#if bean.country}
										<div class="flex items-center text-sm">
											<MapPin class="mr-2 w-4 h-4 text-muted-foreground" />
											<span>{bean.country_full_name || bean.country}</span>
											{#if bean.region}
												<span class="ml-1 text-muted-foreground">• {bean.region}</span>
											{/if}
										</div>
									{/if}

									{#if bean.price}
										<div class="flex items-center text-sm">
											<DollarSign class="mr-2 w-4 h-4 text-muted-foreground" />
											<span class="font-medium">{formatPrice(bean.price, bean.currency)}</span>
											{#if bean.weight}
												<span class="ml-2 text-muted-foreground">• {bean.weight}g</span>
											{/if}
										</div>
									{/if}

									{#if bean.process || bean.roast_level || bean.variety}
										<div class="flex flex-wrap gap-1">
											{#if bean.roast_level}
												<span class="inline-flex items-center bg-secondary px-2 py-1 rounded-full font-medium text-xs">
													{bean.roast_level}
												</span>
											{/if}
											{#if bean.process}
												<span class="inline-flex items-center bg-secondary px-2 py-1 rounded-full font-medium text-xs">
													{bean.process}
												</span>
											{/if}
											{#if bean.variety}
												<span class="inline-flex items-center bg-secondary px-2 py-1 rounded-full font-medium text-xs">
													{bean.variety}
												</span>
											{/if}
										</div>
									{/if}

									{#if bean.tasting_notes && bean.tasting_notes.length > 0}
										<div class="flex flex-wrap gap-1">
											{#each bean.tasting_notes.slice(0, 3) as note}
												<span class="inline-flex items-center bg-primary/10 px-2 py-1 rounded-full text-xs">
													{note}
												</span>
											{/each}
											{#if bean.tasting_notes.length > 3}
												<span class="text-muted-foreground text-xs">+{bean.tasting_notes.length - 3} more</span>
											{/if}
										</div>
									{/if}

									{#if bean.in_stock !== null}
										<div class="flex justify-between items-center">
											<span class="text-sm {bean.in_stock ? 'text-green-600' : 'text-red-600'}">
												{bean.in_stock ? '✅ In stock' : '❌ Out of stock'}
											</span>
											<div class="flex gap-2">
												<Button variant="outline" size="sm" href={getBeanUrl(bean)}>
													View Details
												</Button>
												{#if bean.url}
													<Button variant="outline" size="sm" onclick={() => window.open(bean.url, '_blank')}>
														Buy
													</Button>
												{/if}
											</div>
										</div>
									{:else if bean.url}
										<div class="flex justify-end">
											<Button variant="outline" size="sm" href={getBeanUrl(bean)}>
												View Details
											</Button>
										</div>
									{/if}
								</div>
							</CardContent>
						</Card>
					{/each}
				</div>

				<!-- Pagination -->
				{#if totalPages > 1}
					<div class="flex justify-center items-center space-x-2">
						<Button
							variant="outline"
							size="sm"
							disabled={currentPage <= 1}
							onclick={() => changePage(currentPage - 1)}
						>
							Previous
						</Button>

						{#each Array.from({length: Math.min(5, totalPages)}, (_, i) => {
							const startPage = Math.max(1, currentPage - 2);
							return startPage + i;
						}).filter(p => p <= totalPages) as pageNum}
							<Button
								variant={pageNum === currentPage ? "default" : "outline"}
								size="sm"
								onclick={() => changePage(pageNum)}
							>
								{pageNum}
							</Button>
						{/each}

						<Button
							variant="outline"
							size="sm"
							disabled={currentPage >= totalPages}
							onclick={() => changePage(currentPage + 1)}
						>
							Next
						</Button>
					</div>
				{/if}
			{/if}

			<!-- Empty State -->
			{#if !loading && !error && searchResults && searchResults.length === 0}
				<div class="py-12 text-center">
					<Coffee class="mx-auto mb-4 w-12 h-12 text-muted-foreground" />
					<h3 class="mb-2 font-semibold text-xl">No coffee beans found</h3>
					<p class="mb-4 text-muted-foreground">Try adjusting your search criteria or clearing some filters.</p>
					<Button onclick={clearFilters}>Clear Filters</Button>
				</div>
			{/if}
		</main>
	</div>
</div>
