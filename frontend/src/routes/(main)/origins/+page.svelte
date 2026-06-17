<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Globe } from "lucide-svelte";
	import { type Country, type CountryCode } from "$lib/api.js";
	import type { OriginSearchResult } from "$lib/originsApi.js";
	import UniversalOriginSearch from "$lib/components/UniversalOriginSearch.svelte";
	import "iconify-icon";
	import type { PageData } from "./$types";
	import { replaceState } from "$app/navigation";
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

	let searchQuery = $state(page.url.searchParams.get("query") || "");

	$effect(() => {
		const url = new URL(page.url);
		const currentQuery = url.searchParams.get("query") || "";
		if (currentQuery === searchQuery) return;

		if (searchQuery) {
			url.searchParams.set("query", searchQuery);
		} else {
			url.searchParams.delete("query");
		}
		replaceState(url, {});
	});
</script>

<svelte:head>
	<title>Search | Coffee Origins | Kissaten</title>
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

	<!-- Universal Search -->
	<UniversalOriginSearch
		{defaultResults}
		bind:searchQuery
	/>

	<!-- Empty State (Optional override or handled by UniversalOriginSearch) -->
	{#if searchQuery && defaultResults.length === 0}
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
				}}
				class="bg-orange-600 hover:bg-orange-700 dark:bg-emerald-600 dark:hover:bg-emerald-700 text-white"
				>Clear Search</Button
			>
		</div>
	{/if}
</div>
