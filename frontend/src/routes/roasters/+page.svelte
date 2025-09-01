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
		<h1 class="mb-4 font-bold text-4xl">Coffee Roasters</h1>
		<p class="mx-auto max-w-2xl text-muted-foreground text-xl">
			Discover specialty coffee roasters from around the world and explore their unique bean selections.
		</p>
	</div>

	<!-- Search Bar -->
	<div class="mx-auto mb-8 max-w-md">
		<div class="relative">
			<Search class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
			<Input
				bind:value={searchQuery}
				placeholder="Search roasters..."
				class="pl-10"
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
		<div class="text-muted-foreground text-center">
			Showing {filteredRoasters.length} of {roasters.length} roasters
		</div>
	{/if}

	<!-- Empty State -->
	{#if filteredRoasters && filteredRoasters.length === 0 && searchQuery}
		<div class="py-12 text-center">
			<Coffee class="mx-auto mb-4 w-12 h-12 text-muted-foreground" />
			<h3 class="mb-2 font-semibold text-xl">No roasters found</h3>
			<p class="mb-4 text-muted-foreground">Try searching with different keywords.</p>
			<Button onclick={() => searchQuery = ''}>Clear Search</Button>
		</div>
	{/if}
</div>
