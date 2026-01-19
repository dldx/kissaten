<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Coffee, Search } from "lucide-svelte";
	import RoasterCard from "$lib/components/RoasterCard.svelte";
	import RoasterStickerWall from "$lib/components/RoasterStickerWall.svelte";
	import { type Roaster } from "$lib/api.js";
	import type { PageData } from "./$types";
	import { scale, fade } from "svelte/transition";
	import { LayoutGrid, Sticker } from "lucide-svelte";

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	let roasters: Roaster[] = $state(data.roasters);
	let searchQuery = $state("");
	let debouncedSearchQuery = $state("");
	let showStickerWall = $state(false);
	let debounceTimer: any;

	function handleSearchInput(e: Event & { currentTarget: HTMLInputElement }) {
		const value = e.currentTarget.value;
		searchQuery = value;

		if (debounceTimer) clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			debouncedSearchQuery = value;
		}, 300);
	}

	const filteredRoasters = $derived.by(() => {
		if (!searchQuery.trim()) {
			return roasters;
		} else {
			const query = searchQuery.toLowerCase();
			return roasters.filter(
				(roaster) =>
					roaster.name.toLowerCase().includes(query) ||
					(roaster.location &&
						roaster.location.toLowerCase().includes(query)),
			);
		}
	});
</script>

<svelte:head>
	<title>Coffee Roasters - Kissaten</title>
	<meta
		name="description"
		content="Browse coffee roasters from around the world"
	/>
</svelte:head>

<div class="mx-auto px-4 py-8 container">
	<!-- Header -->
	<div class="mb-12 text-center">
		<h1
			class="varietal-title-shadow mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl"
		>
			Coffee Roasters
		</h1>
		<p
			class="varietal-description-shadow mx-auto mb-6 max-w-3xl text-gray-600 dark:text-cyan-300/80 text-xl"
		>
			From small artisanal roasters to established coffee houses, each
			brings their own expertise and passion to the craft.
		</p>
	</div>

	<!-- Search Bar -->
	<div class="mx-auto mb-8 max-w-md">
		<div class="relative">
			<Search
				class="top-1/2 left-3 absolute w-4 h-4 text-gray-500 dark:text-cyan-400/70 -translate-y-1/2 transform"
			/>
			<input
				value={searchQuery}
				oninput={handleSearchInput}
				placeholder="Search roasters by name or country..."
				class="w-full h-10 px-3 py-2 text-sm bg-white dark:bg-slate-700/60 pl-10 border border-gray-200 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 focus:ring-1 focus:ring-orange-500 dark:focus:ring-emerald-500/50 text-gray-900 dark:placeholder:text-cyan-400/70 dark:text-cyan-200 placeholder:text-gray-500 rounded-md outline-none transition-all"
			/>
		</div>
	</div>

	<!-- View Toggle -->
	<div class="flex justify-center mb-8">
		<div
			class="justify-center justify-self-center items-center grid grid-cols-2 bg-gray-100 dark:bg-slate-700/60 p-1 border border-gray-200 dark:border-slate-600 rounded-lg w-fit"
		>
			<button
				onclick={() => (showStickerWall = false)}
				class="px-4 py-2 text-sm flex flex-col items-center justify-center gap-2 font-medium rounded-md transition-all {!showStickerWall
					? 'bg-white dark:bg-slate-700 text-gray-900 dark:text-cyan-100 shadow-sm'
					: 'text-gray-500 dark:text-cyan-400/60 hover:text-gray-900 dark:hover:text-cyan-100'}"
			>
				<LayoutGrid class="w-6 h-6" /> Grid
			</button>
			<button
				onclick={() => (showStickerWall = true)}
				class="px-4 py-2 text-sm flex flex-col items-center justify-center gap-2 font-medium rounded-md transition-all {showStickerWall
					? 'bg-white dark:bg-slate-700 text-gray-900 dark:text-cyan-100 shadow-sm'
					: 'text-gray-500 dark:text-cyan-400/60 hover:text-gray-900 dark:hover:text-cyan-100'}"
			>
				<Sticker class="w-6 h-6" /> Stickers
			</button>
		</div>
	</div>

	<!-- Roasters Content -->
	{#if filteredRoasters && (filteredRoasters.length > 0 || !searchQuery)}
		<!-- Results Summary -->
		<div
			class="mb-4 text-gray-600 dark:text-cyan-400/80 text-right text-sm"
		>
			{#if filteredRoasters.length === roasters.length}
				{roasters.length} roasters
			{:else}
				Showing {filteredRoasters.length} of {roasters.length} roasters
			{/if}
		</div>

		{#if showStickerWall}
			<div in:fade={{ duration: 300 }}>
				<RoasterStickerWall {roasters} {debouncedSearchQuery} />
			</div>
		{:else}
			<div
				class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 mb-8"
				in:fade={{ duration: 300 }}
			>
				{#each filteredRoasters as roaster, roaster_index (roaster.id)}
					<div in:scale|global={{ delay: 50 * roaster_index }}>
						<RoasterCard {roaster} />
					</div>
				{/each}
			</div>
		{/if}
	{/if}

	<!-- Empty State -->
	{#if filteredRoasters && filteredRoasters.length === 0 && searchQuery}
		<div class="py-12 text-center">
			<Coffee
				class="mx-auto mb-4 w-12 h-12 text-gray-500 dark:text-cyan-400/70"
			/>
			<h3
				class="mb-2 font-semibold text-gray-900 dark:text-cyan-100 text-xl"
			>
				No roasters found
			</h3>
			<p class="mb-4 text-gray-600 dark:text-cyan-300/80">
				Try searching with different keywords.
			</p>
			<Button
				onclick={() => (searchQuery = "")}
				class="bg-orange-600 hover:bg-orange-700 dark:bg-emerald-600 dark:hover:bg-emerald-700 text-white"
				>Clear Search</Button
			>
		</div>
	{/if}
</div>
