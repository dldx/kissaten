<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Select from "$lib/components/ui/select/index.js";
	import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
	import {
		InfiniteLoader,
		LoaderState,
	} from "$lib/components/infinite-scroll";
	import { Coffee, ArrowUp, ArrowDown, Shuffle } from "lucide-svelte";
	import SmartSearch from "./SmartSearch.svelte";
	import SearchFilters from "./SearchFilters.svelte";
	import FilterTags from "./FilterTags.svelte";
	import type { CoffeeBean, Roaster } from "$lib/api.js";
	import { Separator } from "../ui/separator";
	import type { UserDefaults } from "$lib/types/userDefaults";
	import { fade, scale, slide } from "svelte/transition";

	interface Props {
		results: CoffeeBean[];
		maxPossibleScore: number;
		totalResults: number;
		loaderState: LoaderState;
		error: string;
		hasFiltersApplied: boolean;
		onLoadMore: () => Promise<void>;
		onClearFilters: () => void;
		onRetrySearch: () => void;
		smartSearchValue: string;
		smartSearchLoading: boolean;
		smartSearchAvailable: boolean;
		onSmartSearch: (query: string, userDefaults: UserDefaults) => void;
		onImageSearch: (image: File, userDefaults: UserDefaults) => void;

		// Filter props
		searchQuery: string;
		tastingNotesQuery: string;
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
		showFilters: boolean;
		originOptions: { value: string; text: string }[];
		allRoasters: Roaster[];
		roasterLocationOptions: { value: string; text: string }[];
		onSearch: () => void;
		userDefaults: UserDefaults;
	}

	let {
		results,
		maxPossibleScore,
		totalResults,
		loaderState,
		error,
		hasFiltersApplied,
		onLoadMore,
		onClearFilters,
		onRetrySearch,
		smartSearchValue: smartSearchValue = $bindable(),
		smartSearchLoading: smartSearchLoading,
		smartSearchAvailable: smartSearchAvailable,
		onSmartSearch: onSmartSearch,
		onImageSearch: onImageSearch,

		// Filter props
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
		showFilters = $bindable(),
		originOptions,
		allRoasters,
		roasterLocationOptions,
		onSearch,
		userDefaults,
	}: Props = $props();

	function toggleFilters() {
		showFilters = !showFilters;
	}

	function handleRemoveFilter(type: string, value?: string) {
		switch (type) {
			case "search":
				searchQuery = "";
				break;
			case "tasting_notes":
				// For tasting notes, we need to remove the specific note from the query
				if (tastingNotesQuery && value) {
					const notes = tastingNotesQuery
						.split(/[&|]/)
						.map((note) => note.trim().replace(/"/g, ""))
						.filter((note) => note !== value);
					tastingNotesQuery =
						notes.length > 0
							? notes.map((note) => `"${note}"`).join("&")
							: "";
				}
				break;
			case "roaster":
				roasterFilter = roasterFilter.filter((r) => r !== value);
				break;
			case "roaster_location":
				roasterLocationFilter = roasterLocationFilter.filter(
					(rl) => rl !== value,
				);
				break;
			case "origin":
				originFilter = originFilter.filter((o) => o !== value);
				break;
			case "roast_level":
				roastLevelFilter = "";
				break;
			case "roast_profile":
				roastProfileFilter = "";
				break;
			case "process":
				processFilter = "";
				break;
			case "variety":
				varietyFilter = "";
				break;
			case "price_range":
				minPrice = "";
				maxPrice = "";
				break;
			case "weight_range":
				minWeight = "";
				maxWeight = "";
				break;
			case "elevation_range":
				minElevation = "";
				maxElevation = "";
				break;
			case "region":
				regionFilter = "";
				break;
			case "producer":
				producerFilter = "";
				break;
			case "farm":
				farmFilter = "";
				break;
			case "in_stock":
				inStockOnly = false;
				break;
			case "is_decaf":
				isDecaf = undefined;
				break;
			case "is_single_origin":
				isSingleOrigin = undefined;
				break;
		}
		// Trigger search after removing filter
		onSearch();
	}

	const sortLabels = [
		{ value: "date_added", label: "Freshness" },
		{ value: "relevance", label: "Relevance" },
		{ value: "roaster", label: "Roaster" },
		{ value: "price", label: "Price" },
		{ value: "name", label: "Name" },
		{ value: "origin", label: "Origin" },
		{ value: "region", label: "Region" },
		{ value: "elevation", label: "Elevation" },
		{ value: "variety", label: "Variety" },
		{ value: "process", label: "Process" },
		{ value: "cupping_score", label: "Cupping Score" },
		{ value: "weight", label: "Weight" },
	];
	const sortTriggerContent = $derived(
		sortLabels.find((f) => f.value === sortBy)?.label ?? "Sort by",
	);
</script>

<main class="flex-1">
	<!-- Results Header -->
	<h1 class="hidden lg:block mb-4 font-bold text-3xl">Coffee Beans</h1>

	<!-- Smart Search -->
	<div class="mb-6">
		<SmartSearch
			bind:value={smartSearchValue}
			loading={smartSearchLoading}
			available={smartSearchAvailable}
			onSearch={onSmartSearch}
			{onImageSearch}
			onToggleFilters={toggleFilters}
			autofocus={false}
			hasActiveFilters={hasFiltersApplied}
			{userDefaults}
		/>
	</div>

	<!-- Filter Tags -->
	<div class="mb-6">
		<FilterTags
			{searchQuery}
			{tastingNotesQuery}
			{roasterFilter}
			{roasterLocationFilter}
			{originFilter}
			{roastLevelFilter}
			{roastProfileFilter}
			{processFilter}
			{varietyFilter}
			{minPrice}
			{maxPrice}
			{minWeight}
			{maxWeight}
			{minElevation}
			{maxElevation}
			{regionFilter}
			{producerFilter}
			{farmFilter}
			{inStockOnly}
			{isDecaf}
			{isSingleOrigin}
			{originOptions}
			{roasterLocationOptions}
			onRemoveFilter={handleRemoveFilter}
			onClearAll={onClearFilters}
		/>
	</div>

	<!-- Advanced Filters -->
	{#if showFilters}
		<div class="lg:hidden bg-muted/50 mb-6 p-4 rounded-lg">
			<SearchFilters
				bind:searchQuery
				bind:tastingNotesQuery
				bind:roasterFilter
				bind:roasterLocationFilter
				bind:originFilter
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
				{originOptions}
				{allRoasters}
				{roasterLocationOptions}
				{onSearch}
				{onClearFilters}
				class=""
			/>
		</div>
	{/if}

	<div class="flex justify-between items-center mb-6">
		<div class="w-full">
			<!-- Sort Options -->
			<div
				class="flex flex-col-reverse sm:flex-row justify-center sm:justify-end items-end gap-2 text-muted-foreground"
			>
				<div
					class="block justify-self-start text-right sm:text-left self-center w-full grow"
				>
					{#if results.length === totalResults}
						{totalResults} beans found
					{:else}
						Showing &nbsp;{results.length} of {totalResults} beans
					{/if}
				</div>
				<div class="flex items-center gap-2">
					<!-- In Stock Only -->
					<input
						type="checkbox"
						id="inStock-bar"
						bind:checked={inStockOnly}
						onchange={onSearch}
						class="border-input rounded"
					/>
					<label for="inStock" class="font-medium text-sm w-max"
						>In stock only</label
					>
					<Select.Root
						type="single"
						name="sortBy"
						bind:value={sortBy}
						onValueChange={onSearch}
					>
						<Select.Trigger class="w-[120px]">
							{sortTriggerContent}
						</Select.Trigger>
						<Select.Content>
							{#each sortLabels as label}
								<Select.Item
									value={label.value}
									label={label.label}
								/>
							{/each}
						</Select.Content>
					</Select.Root>
					<Button
						variant="outline"
						size="sm"
						onclick={() => {
							sortOrder =
								sortOrder === "desc"
									? "asc"
									: sortOrder === "asc"
										? "random"
										: "desc";
							onSearch();
						}}
						class="flex items-center gap-1 px-3 py-2 text-sm"
					>
						{#if sortOrder === "asc"}
							<ArrowUp class="w-3 h-3" />
						{:else if sortOrder === "desc"}
							<ArrowDown class="w-3 h-3" />
						{:else}
							<Shuffle class="w-3 h-3" />
						{/if}
					</Button>
				</div>
			</div>
		</div>
	</div>

	<!-- Error State -->
	{#if error}
		<div class="py-12 text-center">
			<p class="mb-4 text-red-500">{error}</p>
			<Button onclick={onRetrySearch}>Try Again</Button>
		</div>
	{:else}
		<!-- Infinite Scroll Results -->
		<InfiniteLoader
			{loaderState}
			triggerLoad={onLoadMore}
			intersectionOptions={{ rootMargin: "0px 0px 200px 0px" }}
			>{@const filteredResults = results.filter(
				(bean) => bean.score >= maxPossibleScore,
			)}
			{#if filteredResults.length > 0}
				<div
					class="gap-6 grid grid-cols-1 md:grid-cols-2 {showFilters
						? 'xl:grid-cols-3'
						: 'xl:grid-cols-4'} mb-8"
				>
					{#each filteredResults as bean, bean_index (bean.id)}
						<a
							href={"/roasters" + bean.bean_url_path}
							class="block"
							in:scale|global={{ delay: (bean_index % 10) * 50 }}
						>
							<CoffeeBeanCard {bean} class="h-full" />
						</a>
					{/each}
				</div>
				{#if sortBy === "relevance"}
					<div class="flex items-center gap-2 my-16 w-full">
						<div class="flex-1">
							<Separator />
						</div>
						<span class="px-2 text-muted-foreground text-xs"
							>Similar beans</span
						>
						<div class="flex-1">
							<Separator />
						</div>
					</div>
				{/if}
			{/if}
			<div
				class="gap-6 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 mb-8"
			>
				{#each results.filter((bean) => bean.score < maxPossibleScore) as bean, bean_index (bean.id)}
					<a
						href={"/roasters" + bean.bean_url_path}
						class="block"
						in:scale|global={{ delay: (bean_index % 10) * 50 }}
					>
						<CoffeeBeanCard {bean} class="h-full" />
					</a>
				{/each}
			</div>

			{#snippet loading()}
				<div class="flex flex-col items-center space-y-4">
					<div
						class="inline-block border-primary border-b-2 rounded-full w-6 h-6 animate-spin"
					></div>
					<p class="text-muted-foreground text-sm">
						Loading more beans...
					</p>
				</div>
			{/snippet}

			{#snippet noResults()}
				<div class="py-12 text-center">
					<Coffee
						class="mx-auto mb-4 w-12 h-12 text-muted-foreground"
					/>
					<h3 class="mb-2 font-semibold text-xl">
						No coffee beans found
					</h3>
					<p class="mb-4 text-muted-foreground">
						Try adjusting your search criteria or clearing some
						filters.
					</p>
					<Button onclick={onClearFilters}>Clear Filters</Button>
				</div>
			{/snippet}

			{#snippet noData()}
				<div class="py-8 text-center">
					<p class="text-muted-foreground">No more beans found!</p>
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
