<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Search, Coffee, Citrus, MapPin, Mountain, Flame, Scale, User, TreePine, Droplets, Leaf, CreditCard } from "lucide-svelte";
	import Svelecte from 'svelecte';
	import Separator from '$lib/components/ui/separator/separator.svelte';
	import type { Roaster } from '$lib/api.js';

	interface OriginOption {
		value: string;
		text: string;
	}

	interface RoasterLocationOption {
		value: string;
		text: string;
	}

	interface Props {
		// Search queries
		searchQuery: string;
		tastingNotesQuery: string;

		// Filters
		roasterFilter: string[];
		roasterLocationFilter: string[];
		originFilter: string[];
		roastLevelFilter: string;
		roastProfileFilter: string;
		processFilter: string;
		varietyFilter: string;
		minPrice: string;
		maxPrice: string;
		minWeight: string;
		maxWeight: string;
		minElevation: string;
		maxElevation: string;
		regionFilter: string;
		producerFilter: string;
		farmFilter: string;
		inStockOnly: boolean;
		isDecaf: boolean | undefined;
		isSingleOrigin: boolean | undefined;
		sortBy: string;
		sortOrder: string;

		// Dropdown options
		originOptions: OriginOption[];
		allRoasters: Roaster[];
		roasterLocationOptions: RoasterLocationOption[];

		// Mobile state
		showFilters: boolean;

		// Callbacks
		onSearch: () => void;
		onClearFilters: () => void;
	}

	let {
		searchQuery = $bindable(),
		tastingNotesQuery = $bindable(),
		roasterFilter = $bindable(),
		roasterLocationFilter = $bindable(),
		originFilter = $bindable(),
		roastLevelFilter = $bindable(),
		roastProfileFilter = $bindable(),
		processFilter = $bindable(),
		varietyFilter = $bindable(),
		minPrice = $bindable(),
		maxPrice = $bindable(),
		minWeight = $bindable(),
		maxWeight = $bindable(),
		minElevation = $bindable(),
		maxElevation = $bindable(),
		regionFilter = $bindable(),
		producerFilter = $bindable(),
		farmFilter = $bindable(),
		inStockOnly = $bindable(),
		isDecaf = $bindable(),
		isSingleOrigin = $bindable(),
		sortBy = $bindable(),
		sortOrder = $bindable(),
		originOptions,
		allRoasters,
		roasterLocationOptions,
		showFilters = $bindable(),
		onSearch,
		onClearFilters
	}: Props = $props();

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

	function handleKeyPress(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			onSearch();
		}
	}
</script>

<div class="space-y-6 lg:w-80">
	<div class="space-y-4">
		<div class="flex items-center gap-2 w-full">
			<div class="flex-1">
				<Separator/>
			</div>
			<span class="px-2 text-muted-foreground text-xs">Advanced search</span>
			<div class="flex-1">
				<Separator/>
			</div>
		</div>

		<!-- Regular Search Query -->
		<div>
			<label class="block mb-2 font-medium text-sm" for="searchQuery">Search Query</label>
			<div class="relative">
				<Search class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
				<Input
					bind:value={searchQuery}
					placeholder="Bean names, roasters, origins..."
					class="pl-10"
					onkeypress={handleKeyPress}
				/>
			</div>
		</div>
				<div class="bg-muted/50 mt-2 px-3 py-2 rounded-md text-muted-foreground text-xs">
					<p class="mb-1"><strong>Advanced wildcard syntax:</strong></p>
					<p class="mb-1">• Use <code>|</code> for OR: <code>chocolate|caramel</code></p>
					<p class="mb-1">• Use <code>&</code> for AND: <code>washed&natural</code></p>
					<p class="mb-1">• Use <code>!</code> for NOT: <code>chocolate&!bitter</code></p>
					<p class="mb-1">• Use <code>*</code> and <code>?</code> for wildcards: <code>ge*sha</code></p>
					<p>• Use <code>()</code> for grouping: <code>berry&(lemon|lime)</code></p>
				</div>

		<!-- Tasting Notes Search -->
		<div>
			<label class="block mb-2 font-medium text-sm" for="tastingNotesQuery">Tasting Notes Search</label>
			<div class="relative">
				<Citrus class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
				<Input
					id="tastingNotesQuery"
					bind:value={tastingNotesQuery}
					placeholder="chocolate|caramel, berry&passion fruit..."
					class="pl-10"
					onkeypress={handleKeyPress}
				/>
			</div>
		</div>

		<!-- Roaster Location Filter -->
		<div>
			<label class="block mb-2 font-medium text-sm" for="roasterLocationFilter">Roaster Location</label>
			<Svelecte
				bind:value={roasterLocationFilter}
				options={roasterLocationOptions || []}
				placeholder="Filter by roaster location..."
				searchable
				clearable
				multiple
				class="w-full"
				onChange={onSearch}
			/>
		</div>

		<!-- Roaster Filter -->
		<div>
			<label class="block mb-2 font-medium text-sm" for="roasterFilter">Roaster</label>
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
				onChange={onSearch}
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
			<label class="block mb-2 font-medium text-sm" for="originFilter">Coffee Origin</label>
			<Svelecte
				bind:value={originFilter}
				options={originOptions || []}
				placeholder="Filter by origin country..."
				searchable
				clearable
				multiple
				class="w-full"
				onChange={onSearch}
			/>
		</div>

		<!-- Region Filter -->
		<div>
			<label class="block mb-2 font-medium text-sm" for="regionFilter">Region</label>
			<div class="relative">
				<MapPin class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
				<Input
					id="regionFilter"
					bind:value={regionFilter}
					placeholder="Antioquia|Huila, *gacheffe..."
					class="pl-10"
					onkeypress={handleKeyPress}
				/>
			</div>
		</div>

		<!-- Producer Filter -->
		<div>
			<label class="block mb-2 font-medium text-sm" for="producerFilter">Producer</label>
			<div class="relative">
				<User class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
				<Input
					id="producerFilter"
					bind:value={producerFilter}
					placeholder="Jijon&!Pepe"
					class="pl-10"
					onkeypress={handleKeyPress}
				/>
			</div>
		</div>

		<!-- Farm Filter -->
		<div>
			<label class="block mb-2 font-medium text-sm" for="farmFilter">Farm</label>
			<div class="relative">
				<TreePine class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
				<Input
					id="farmFilter"
					bind:value={farmFilter}
					placeholder="La Soledad"
					class="pl-10"
					onkeypress={handleKeyPress}
				/>
			</div>
		</div>

		<!-- Roast Level Filter -->
		<div>
			<label class="block mb-2 font-medium text-sm" for="roastLevelFilter">Roast Level</label>
			<div class="relative">
				<Flame class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
				<Input
					id="roastLevelFilter"
					bind:value={roastLevelFilter}
					placeholder="Light|Medium-Light|Medium|Medium-Dark|Dark"
					class="pl-10"
					onkeypress={handleKeyPress}
				/>
			</div>
		</div>

		<!-- Roast Profile Filter -->
		<div>
			<label class="block mb-2 font-medium text-sm" for="roastProfileFilter">Roast Profile</label>
			<div class="relative">
				<Coffee class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
			<Input
				id="roastProfileFilter"
				bind:value={roastProfileFilter}
				class="pl-10"
				placeholder="Filter|Espresso|Omni"
					onkeypress={handleKeyPress}
				/>
			</div>
		</div>

		<!-- Process Filter -->
		<div>
			<label class="block mb-2 font-medium text-sm" for="processFilter">Process</label>
			<div class="relative">
				<Droplets class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
				<Input
					id="processFilter"
					bind:value={processFilter}
					placeholder="Washed|Natural&!Anaerobic"
					class="pl-10"
					onkeypress={handleKeyPress}
				/>
			</div>
		</div>

		<!-- Variety Filter -->
		<div>
			<label class="block mb-2 font-medium text-sm" for="varietyFilter">Variety</label>
			<div class="relative">
				<Leaf class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
				<Input
					id="varietyFilter"
					bind:value={varietyFilter}
					placeholder="Catuai|Bourbon, Ge*sha..."
					class="pl-10"
					onkeypress={handleKeyPress}
				/>
			</div>
		</div>

		<!-- Elevation Range -->
		<div>
			<span class="block mb-2 font-medium text-sm">Elevation (meters)</span>
			<div class="flex gap-2">
				<div class="relative flex-1">
					<Mountain class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
					<Input
						id="minElevation"
						bind:value={minElevation}
						placeholder="Min"
						type="number"
						class="pl-10"
						onkeypress={handleKeyPress}
					/>
				</div>
				<div class="relative flex-1">
					<Mountain class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
					<Input
						id="maxElevation"
						bind:value={maxElevation}
						placeholder="Max"
						type="number"
						class="pl-10"
						onkeypress={handleKeyPress}
					/>
				</div>
			</div>
		</div>

		<!-- Price Range -->
		<div>
			<span class="block mb-2 font-medium text-sm">Price Range</span>
			<div class="flex gap-2">
				<div class="relative flex-1">
					<CreditCard class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
					<Input
						id="minPrice"
						bind:value={minPrice}
						placeholder="Min"
						type="number"
						step="0.01"
						class="pl-10"
						onkeypress={handleKeyPress}
					/>
				</div>
				<div class="relative flex-1">
					<CreditCard class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
					<Input
						id="maxPrice"
						bind:value={maxPrice}
						placeholder="Max"
						type="number"
						step="0.01"
						class="pl-10"
						onkeypress={handleKeyPress}
					/>
				</div>
			</div>
		</div>

		<!-- Weight Range -->
		<div>
			<span class="block mb-2 font-medium text-sm">Weight (grams)</span>
			<div class="flex gap-2">
				<div class="relative flex-1">
					<Scale class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
					<Input
						id="minWeight"
						bind:value={minWeight}
						placeholder="Min"
						type="number"
						class="pl-10"
						onkeypress={handleKeyPress}
					/>
				</div>
				<div class="relative flex-1">
					<Scale class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
					<Input
						id="maxWeight"
						bind:value={maxWeight}
						placeholder="Max"
						type="number"
						class="pl-10"
						onkeypress={handleKeyPress}
					/>
				</div>
			</div>
		</div>

		<!-- In Stock Only -->
		<div class="flex items-center space-x-2">
			<input
				type="checkbox"
				id="inStock"
				bind:checked={inStockOnly}
				onchange={onSearch}
				class="border-input rounded"
			/>
			<label for="inStock" class="font-medium text-sm">In stock only</label>
		</div>

		<!-- Decaf Filter -->
		<div class="space-y-2">
			<span class="block font-medium text-sm">Decaf</span>
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
							onSearch();
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
							onSearch();
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
							onSearch();
						}}
						class="border-input"
					/>
					<label for="decaf-no" class="text-sm">Regular only</label>
				</div>
			</div>
		</div>

		<!-- Single Origin vs Blend Filter -->
		<div class="space-y-2">
			<span class="block font-medium text-sm">Origin Type</span>
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
							onSearch();
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
							onSearch();
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
							onSearch();
						}}
						class="border-input"
					/>
					<label for="origin-blend" class="text-sm">Blends</label>
				</div>
			</div>
		</div>

		<!-- Sort Options -->
		<div>
			<label class="block mb-2 font-medium text-sm" for="sortBy">Sort by</label>
			<select id="sortBy" bind:value={sortBy} onchange={onSearch} class="bg-background px-3 py-2 border border-input rounded-md w-full text-sm">
				<option value="name">Name</option>
				<option value="roaster">Roaster</option>
				<option value="price">Price</option>
				<option value="weight">Weight</option>
				<option value="origin">Origin</option>
				<option value="region">Region</option>
				<option value="elevation">Elevation</option>
				<option value="variety">Variety</option>
				<option value="process">Process</option>
				<option value="cupping_score">Cupping Score</option>
				<option value="scraped_at">Date Added</option>
			</select>
			<label class="block mt-2 mb-2 font-medium text-sm" for="sortOrder">Sort order</label>
			<select id="sortOrder" bind:value={sortOrder} onchange={onSearch} class="bg-background px-3 py-2 border border-input rounded-md w-full text-sm">
				<option value="asc">Ascending</option>
				<option value="desc">Descending</option>
			</select>
		</div>

		<!-- Action Buttons -->
		<div class="space-y-2">
			<Button class="w-full" onclick={onSearch}>
				<Search class="mr-2 w-4 h-4" />
				Apply Filters
			</Button>
			<Button variant="outline" class="w-full" onclick={onClearFilters}>
				Clear All
			</Button>
		</div>
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
