<script lang="ts">
	import { Input } from "$lib/components/ui/input/index.js";
	import { Search, Loader2 } from "lucide-svelte";
	import { searchOrigins, type OriginSearchResult } from "$lib/originsApi.js";
	import OriginResultCard from "$lib/components/OriginResultCard.svelte";
	import { scale } from "svelte/transition";

	interface Props {
		defaultResults: OriginSearchResult[];
		placeholder?: string;
		countryCode?: string;
		regionSlug?: string;
		searchQuery?: string;
	}

	let {
		defaultResults,
		placeholder = "Search countries, regions or farms...",
		countryCode,
		regionSlug,
		searchQuery = $bindable(""),
	}: Props = $props();

	let searchResults: OriginSearchResult[] = $state(defaultResults);
	let isSearching = $state(false);
	let searchTimeout: ReturnType<typeof setTimeout>;
	let searchVersion = 0;

	async function performSearch() {
		if (!searchQuery.trim()) {
			searchResults = defaultResults;
			isSearching = false;
			return;
		}

		isSearching = true;
		const thisVersion = ++searchVersion;
		try {
			const response = await searchOrigins(searchQuery, 20, countryCode, regionSlug);
			if (thisVersion !== searchVersion) return; // stale response, discard
			if (response.success && response.data) {
				searchResults = response.data;
			}
		} catch (error) {
			if (thisVersion !== searchVersion) return;
			console.error("Search failed:", error);
		} finally {
			if (thisVersion === searchVersion) {
				isSearching = false;
			}
		}
	}

	$effect(() => {
		clearTimeout(searchTimeout);
		if (searchQuery.trim()) {
			searchTimeout = setTimeout(performSearch, 300);
		} else {
			searchVersion++;
			searchResults = defaultResults;
			isSearching = false;
		}
	});

	// Update results if defaultResults change (e.g. after data reload)
	$effect(() => {
		if (!searchQuery.trim()) {
			searchResults = defaultResults;
		}
	});
</script>

<div class="mx-auto mb-8 max-w-md">
	<div class="relative">
		<Search
			class="top-1/2 left-3 absolute w-4 h-4 text-gray-500 dark:text-cyan-400/70 -translate-y-1/2 transform"
		/>
		<Input
			bind:value={searchQuery}
			{placeholder}
			class="bg-white dark:bg-slate-700/60 pl-10 border-gray-200 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 focus:ring-orange-500 dark:focus:ring-emerald-500/50 text-gray-900 dark:placeholder:text-cyan-400/70 dark:text-cyan-200 placeholder:text-gray-500"
		/>
		{#if isSearching}
			<div class="top-1/2 right-3 absolute -translate-y-1/2 transform">
				<Loader2
					class="w-4 h-4 text-gray-400 dark:text-cyan-400/50 animate-spin"
				/>
			</div>
		{/if}
	</div>
</div>

{#if searchResults}
	<div class="mb-4 text-gray-600 dark:text-cyan-400/80 text-right">
		{#if !searchQuery.trim()}
			{@const type = searchResults[0]?.type}
			{searchResults.length}
			{#if type === "country"}
				{searchResults.length === 1 ? "country" : "countries"}
			{:else if type === "region"}
				{searchResults.length === 1 ? "region" : "regions"}
			{:else if type === "farm"}
				{searchResults.length === 1 ? "farm" : "farms"}
			{:else}
				{searchResults.length === 1 ? "result" : "results"}
			{/if}
		{:else}
			Showing {searchResults.length} results for "{searchQuery}"
		{/if}
	</div>
	<div
		class="gap-4 sm:gap-6 grid grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 mb-8"
	>
		{#each searchResults as result, result_index (result.type + result.country_code + (result.region_slug || "") + (result.farm_slug || ""))}
			<div in:scale|global={{ delay: (result_index % 20) * 30 }}>
				<OriginResultCard {result} />
			</div>
		{/each}
	</div>

	{#if searchResults.length === 0 && searchQuery && !isSearching}
		<div class="py-12 text-center">
			<Search
				class="mx-auto mb-4 w-12 h-12 text-gray-500 dark:text-cyan-400/70"
			/>
			<h3 class="mb-2 font-semibold text-gray-900 dark:text-cyan-100 text-xl">
				No results found
			</h3>
			<p class="text-gray-600 dark:text-cyan-300/80">
				Try searching with different keywords like country, region or farm
				name.
			</p>
		</div>
	{/if}
{/if}
