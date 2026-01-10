<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Globe, Search, Loader2 } from "lucide-svelte";
	import { type Country, type CountryCode } from "$lib/api.js";
	import { searchOrigins, type OriginSearchResult } from "$lib/originsApi.js";
	import OriginResultCard from "$lib/components/OriginResultCard.svelte";
	import "iconify-icon";
	import type { PageData } from "./$types";
	import { scale } from "svelte/transition";
	import { goto } from "$app/navigation";
	import { page } from "$app/state";

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	// Default results to show when not searching
	let defaultResults: OriginSearchResult[] = $derived(
		data.countries?.map((c) => ({
			type: "country" as const,
			name: c.country_name,
			country_code: c.country_code,
			country_name: c.country_name,
			bean_count: c.bean_count || 0,
		})),
	);

	let searchResults: OriginSearchResult[] = $derived(defaultResults);
	let searchQuery = $state(page.url.searchParams.get("query") || "");
	let isSearching = $state(false);
	let searchTimeout: ReturnType<typeof setTimeout>;

	async function performSearch() {
		if (!searchQuery.trim()) {
			searchResults = defaultResults;
			isSearching = false;
			return;
		}

		isSearching = true;
		try {
			const response = await searchOrigins(searchQuery);
			goto(
				`/origins?${new URLSearchParams({ query: searchQuery }).toString()}`,
				{
					replaceState: false,
					noScroll: true,
					keepFocus: true,
				},
			);
			if (response.success && response.data) {
				searchResults = response.data;
			}
		} catch (error) {
			console.error("Search failed:", error);
		} finally {
			isSearching = false;
		}
	}

	$effect(() => {
		clearTimeout(searchTimeout);
		if (searchQuery.trim()) {
			searchTimeout = setTimeout(performSearch, 300);
		} else {
			searchResults = defaultResults;
			isSearching = false;
		}
	});
</script>

<svelte:head>
	<title>Search - Coffee Origins - Kissaten</title>
	<meta
		name="description"
		content="Explore coffee beans by their country, region or farm of origin"
	/>
</svelte:head>

<div class="mx-auto px-4 py-8 container">
	<!-- Header -->
	<div class="mb-12 text-center">
		<h1
			class="varietal-title-shadow mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl"
		>
			Coffee Origins
		</h1>
		<p
			class="varietal-description-shadow mx-auto mb-6 max-w-3xl text-gray-600 dark:text-cyan-300/80 text-xl"
		>
			Discover coffee beans from different countries, regions and farms
			around the world, each with their unique varietals, terroir and
			flavour profiles.
		</p>
	</div>

	<!-- Search Bar -->
	<div class="mx-auto mb-8 max-w-md">
		<div class="relative">
			<Search
				class="top-1/2 left-3 absolute w-4 h-4 text-gray-500 dark:text-cyan-400/70 -translate-y-1/2 transform"
			/>
			<Input
				bind:value={searchQuery}
				placeholder="Search countries, regions or farms..."
				class="bg-white dark:bg-slate-700/60 pl-10 border-gray-200 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 focus:ring-orange-500 dark:focus:ring-emerald-500/50 text-gray-900 dark:placeholder:text-cyan-400/70 dark:text-cyan-200 placeholder:text-gray-500"
			/>
			{#if isSearching}
				<div
					class="top-1/2 right-3 absolute -translate-y-1/2 transform"
				>
					<Loader2
						class="w-4 h-4 text-gray-400 dark:text-cyan-400/50 animate-spin"
					/>
				</div>
			{/if}
		</div>
	</div>

	<!-- Countries Grid -->
	{#if searchResults}
		<!-- Results Summary -->
		<div class="mb-4 text-gray-600 dark:text-cyan-400/80 text-right">
			{#if !searchQuery.trim()}
				{searchResults?.length} countries
			{:else}
				Showing {searchResults?.length} results for "{searchQuery}"
			{/if}
		</div>
		<div
			class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 mb-8"
		>
			{#each searchResults as result, result_index (result.type + result.country_code + (result.region_slug || "") + (result.farm_slug || ""))}
				<div in:scale|global={{ delay: result_index * 50 }}>
					<OriginResultCard {result} />
				</div>
			{/each}
		</div>
	{/if}

	<!-- Empty State -->
	{#if searchResults && searchResults?.length === 0 && searchQuery && !isSearching}
		<div class="py-12 text-center">
			<Globe
				class="mx-auto mb-4 w-12 h-12 text-gray-500 dark:text-cyan-400/70"
			/>
			<h3
				class="mb-2 font-semibold text-gray-900 dark:text-cyan-100 text-xl"
			>
				No origins found
			</h3>
			<p class="mb-4 text-gray-600 dark:text-cyan-300/80">
				Try searching with different keywords like country, region or
				farm name.
			</p>
			<Button
				onclick={() => {
					searchQuery = "";
					searchResults = defaultResults;
				}}
				class="bg-orange-600 hover:bg-orange-700 dark:bg-emerald-600 dark:hover:bg-emerald-700 text-white"
				>Clear Search</Button
			>
		</div>
	{/if}
</div>
