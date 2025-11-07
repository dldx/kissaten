<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Globe, Search } from "lucide-svelte";
	import { type Country, type CountryCode } from '$lib/api.js';
	import OriginCard from '$lib/components/OriginCard.svelte';
	import 'iconify-icon';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	let countries: Country[] = $state(data.countries);
	let countryCodes: CountryCode[] = $state(data.countryCodes);
	let filteredCountries: Country[] = $state(data.countries);
	let searchQuery = $state('');

	function filterCountries() {
		if (!searchQuery.trim()) {
			filteredCountries = countries;
		} else {
			const query = searchQuery.toLowerCase();
			filteredCountries = countries.filter(country =>
				country.country_name.toLowerCase().includes(query) ||
				country.country_code.toLowerCase().includes(query)
			);
		}
	}

	$effect(() => {
		filterCountries();
	});
</script>

<svelte:head>
	<title>Coffee Origins by Country - Kissaten</title>
	<meta name="description" content="Explore coffee beans by their country of origin" />
</svelte:head>

<div class="mx-auto px-4 py-8 container">
	<!-- Header -->
	<div class="mb-12 text-center">
		<h1 class="varietal-title-shadow mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl">
			Coffee Origins
		</h1>
		<p class="varietal-description-shadow mx-auto mb-6 max-w-3xl text-gray-600 dark:text-cyan-300/80 text-xl">
			Discover coffee beans from different countries and regions around the world, each with their unique varietals, terroir and flavour profiles.
		</p>
	</div>

	<!-- Search Bar -->
	<div class="mx-auto mb-8 max-w-md">
		<div class="relative">
			<Search class="top-1/2 left-3 absolute w-4 h-4 text-gray-500 dark:text-cyan-400/70 -translate-y-1/2 transform" />
			<Input
				bind:value={searchQuery}
				placeholder="Search countries..."
				class="bg-white dark:bg-slate-700/60 pl-10 border-gray-200 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 focus:ring-orange-500 dark:focus:ring-emerald-500/50 text-gray-900 dark:placeholder:text-cyan-400/70 dark:text-cyan-200 placeholder:text-gray-500"
			/>
		</div>
	</div>

	<!-- Countries Grid -->
	{#if filteredCountries}
		<!-- Results Summary -->
		<div class="mb-4 text-gray-600 dark:text-cyan-400/80 text-right">
			{#if filteredCountries.length === countries.length}
				{countries.length} countries
			{:else}
				Showing {filteredCountries.length} of {countries.length} countries
			{/if}
		</div>
		<div class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 mb-8">
			{#each filteredCountries as country (country.country_code)}
				<OriginCard {country} />
			{/each}
		</div>
	{/if}

	<!-- Empty State -->
	{#if filteredCountries && filteredCountries.length === 0 && searchQuery}
		<div class="py-12 text-center">
			<Globe class="mx-auto mb-4 w-12 h-12 text-gray-500 dark:text-cyan-400/70" />
			<h3 class="mb-2 font-semibold text-gray-900 dark:text-cyan-100 text-xl">No countries found</h3>
			<p class="mb-4 text-gray-600 dark:text-cyan-300/80">Try searching with different keywords.</p>
			<Button onclick={() => searchQuery = ''} class="bg-orange-600 hover:bg-orange-700 dark:bg-emerald-600 dark:hover:bg-emerald-700 text-white">Clear Search</Button>
		</div>
	{/if}
</div>
