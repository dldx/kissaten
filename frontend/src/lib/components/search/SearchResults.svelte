<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Select from "$lib/components/ui/select/index.js";
	import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
	import {
		InfiniteLoader,
		LoaderState,
	} from "$lib/components/infinite-scroll";
	import { Coffee, ArrowUp, ArrowDown } from "lucide-svelte";
	import AISearch from "./AISearch.svelte";
	import SearchFilters from "./SearchFilters.svelte";
	import type { CoffeeBean, Roaster } from "$lib/api.js";

	interface Props {
		results: CoffeeBean[];
		totalResults: number;
		loaderState: LoaderState;
		error: string;
		hasFiltersApplied: boolean;
		onLoadMore: () => Promise<void>;
		onClearFilters: () => void;
		onRetrySearch: () => void;
		aiSearchValue: string;
		aiSearchLoading: boolean;
		aiSearchAvailable: boolean;
		onAISearch: () => void;

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
	}

	let {
		results,
		totalResults,
		loaderState,
		error,
		hasFiltersApplied,
		onLoadMore,
		onClearFilters,
		onRetrySearch,
		aiSearchValue = $bindable(),
		aiSearchLoading,
		aiSearchAvailable,
		onAISearch,

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
	}: Props = $props();

	function toggleFilters() {
		showFilters = !showFilters;
	}
</script>

<main class="flex-1">
	<!-- Results Header -->
	<h1 class="hidden lg:block mb-4 font-bold text-3xl">Coffee Beans</h1>

	<!-- AI Search -->
	<div class="mb-6">
		<AISearch
			bind:value={aiSearchValue}
			loading={aiSearchLoading}
			available={aiSearchAvailable}
			onSearch={onAISearch}
			onToggleFilters={toggleFilters}
			autofocus={false}
		/>
	</div>

	<!-- Mobile Advanced Filters -->
	<div class="lg:hidden">
		{#if showFilters}
			<div class="bg-muted/50 mb-6 p-4 rounded-lg">
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
				/>
			</div>
		{/if}
	</div>

	<div class="flex justify-between items-center mb-6">
		<div class="w-full">
			<!-- Sort Options -->
			<div
				class="flex justify-end items-end gap-2 text-muted-foreground"
			>
				<div class="block justify-self-start self-center w-full grow">
					{#if results.length === totalResults}
						{totalResults} beans found
					{:else}
					<span class="hidden sm:inline">
						Showing &nbsp;</span>{results.length} of {totalResults} beans
					{/if}
				</div>
				<div class="flex items-center gap-2">
				<Select.Root
				type="single"
					name="sortBy"
					bind:value={sortBy}
					onValueChange={onSearch}
				>
					<Select.Trigger class="w-[120px]">
						{#if sortBy === "name"}
							Name
						{:else if sortBy === "roaster"}
							Roaster
						{:else if sortBy === "price"}
							Price
						{:else if sortBy === "weight"}
							Weight
						{:else if sortBy === "origin"}
							Origin
						{:else if sortBy === "region"}
							Region
						{:else if sortBy === "elevation"}
							Elevation
						{:else if sortBy === "variety"}
							Variety
						{:else if sortBy === "process"}
							Process
						{:else if sortBy === "cupping_score"}
							Cupping Score
						{:else if sortBy === "scraped_at"}
							Date Added
						{:else}
							Sort by...
						{/if}
					</Select.Trigger>
					<Select.Content>
						<Select.Item value="name" label="Name" />
						<Select.Item value="roaster" label="Roaster" />
						<Select.Item value="price" label="Price" />
						<Select.Item value="weight" label="Weight" />
						<Select.Item value="origin" label="Origin" />
						<Select.Item value="region" label="Region" />
						<Select.Item value="elevation" label="Elevation" />
						<Select.Item value="variety" label="Variety" />
						<Select.Item value="process" label="Process" />
						<Select.Item value="cupping_score" label="Cupping Score" />
						<Select.Item value="scraped_at" label="Date Added" />
					</Select.Content>
				</Select.Root>
				<Button
					variant="outline"
					size="sm"
					onclick={() => {
						sortOrder = sortOrder === "asc" ? "desc" : "asc";
						onSearch();
					}}
					class="flex items-center gap-1 px-3 py-2 text-sm"
				>
					{#if sortOrder === "asc"}
						<ArrowUp class="w-3 h-3" />
					{:else}
						<ArrowDown class="w-3 h-3" />
					{/if}
				</Button>
				{#if hasFiltersApplied}
					<Button
						variant="outline"
						class="inline justify-self-end"
						onclick={onClearFilters}
					>
						Reset<span class="hidden sm:inline">&nbsp;Filters</span>
					</Button>
				{/if}
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
		>
			<div
				class="gap-6 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 mb-8"
			>
				{#each results as bean (bean.id)}
					<a href={"/roasters" + bean.bean_url_path} class="block">
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
