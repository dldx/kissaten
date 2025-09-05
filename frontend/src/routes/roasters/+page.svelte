<script lang="ts">
	import { goto } from '$app/navigation';
	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Coffee, Search } from "lucide-svelte";
	import RoasterCard from "$lib/components/RoasterCard.svelte";
	import { type Roaster } from '$lib/api.js';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	let roasters: Roaster[] = $state(data.roasters);
	let filteredRoasters: Roaster[] = $state(data.roasters);
	let searchQuery = $state('');

	function filterRoasters() {
		if (!searchQuery.trim()) {
			filteredRoasters = roasters;
		} else {
			const query = searchQuery.toLowerCase();
			filteredRoasters = roasters.filter(roaster =>
				roaster.name.toLowerCase().includes(query) ||
				roaster.location.toLowerCase().includes(query)
			);
		}
	}

	$effect(() => {
		filterRoasters();
	});
</script>

<svelte:head>
	<title>Coffee Roasters - Kissaten</title>
	<meta name="description" content="Browse coffee roasters from around the world" />
</svelte:head>

<div class="mx-auto px-4 py-8 container">
	<!-- Header -->
	<div class="mb-12 text-center">
		<h1 class="varietal-title-shadow mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl">
			Coffee Roasters
		</h1>
		<p class="varietal-description-shadow mx-auto mb-6 max-w-3xl text-gray-600 dark:text-cyan-300/80 text-xl">
			Discover specialty coffee roasters from around the world and explore their unique bean selections.
			From small artisanal roasters to established coffee houses, each brings their own expertise and passion to the craft.
		</p>
		<div class="bg-orange-50 dark:bg-slate-800/60 roaster-info-card-shadow mx-auto p-4 border border-orange-200 dark:border-cyan-500/30 rounded-lg max-w-md">
			<p class="roaster-count-shadow font-medium text-orange-800 dark:text-emerald-300">
				{roasters.length} roasters
			</p>
		</div>
	</div>

	<!-- Search Bar -->
	<div class="mx-auto mb-8 max-w-md">
		<div class="relative">
			<Search class="top-1/2 left-3 absolute w-4 h-4 text-gray-500 dark:text-cyan-400/70 -translate-y-1/2 transform" />
			<Input
				bind:value={searchQuery}
				placeholder="Search roasters..."
				class="bg-white dark:bg-slate-700/60 pl-10 border-gray-200 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 focus:ring-orange-500 dark:focus:ring-emerald-500/50 text-gray-900 dark:placeholder:text-cyan-400/70 dark:text-cyan-200 placeholder:text-gray-500"
			/>
		</div>
	</div>

	<!-- Roasters Grid -->
	{#if filteredRoasters}
		<div class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 mb-8">
			{#each filteredRoasters as roaster (roaster.id)}
				<RoasterCard {roaster} />
			{/each}
		</div>

		<!-- Results Summary -->
		<div class="text-gray-600 dark:text-cyan-400/80 text-center">
			Showing {filteredRoasters.length} of {roasters.length} roasters
		</div>
	{/if}

	<!-- Empty State -->
	{#if filteredRoasters && filteredRoasters.length === 0 && searchQuery}
		<div class="py-12 text-center">
			<Coffee class="mx-auto mb-4 w-12 h-12 text-gray-500 dark:text-cyan-400/70" />
			<h3 class="mb-2 font-semibold text-gray-900 dark:text-cyan-100 text-xl">No roasters found</h3>
			<p class="mb-4 text-gray-600 dark:text-cyan-300/80">Try searching with different keywords.</p>
			<Button onclick={() => searchQuery = ''} class="bg-orange-600 hover:bg-orange-700 dark:bg-emerald-600 dark:hover:bg-emerald-700 text-white">Clear Search</Button>
		</div>
	{/if}
</div>
