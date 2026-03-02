<script lang="ts">
	import type { Roaster } from '$lib/api.js';
	import { MapPin, Building2, Leaf, Search, LayoutGrid, Sticker, ChevronRight } from 'lucide-svelte';
	import { scale, fade } from 'svelte/transition';
	import { Button } from '$lib/components/ui/button';
	import InsightCard from '$lib/components/InsightCard.svelte';
	import RoasterCard from '$lib/components/RoasterCard.svelte';
	import RoasterStickerWall from '$lib/components/RoasterStickerWall.svelte';
	import "iconify-icon";

	interface PageContext {
		breadcrumbs: Array<{ label: string; href?: string }>;
		title: string;
		countryCode?: string;
		locationCode?: string;
		statistics: {
			available_beans: number;
			total_beans: number;
			roaster_count: number;
			city_or_country_count: number;
			city_or_country_label: string;
		};
		insights: {
			originItems?: Array<{ label: string; count: number; href: string }>;
			varietalItems?: Array<{ label: string; count: number; href: string }>;
			cityItems?: Array<{ label: string; count: number; href: string }>;
		};
		roasters: Roaster[];
	}

	interface Props {
		pageContext: PageContext;
		extraContent?: any;  // Svelte 5 snippet for additional content
	}

	let { pageContext, extraContent }: Props = $props();

	// Shared state for search and view toggle
	let searchQuery = $state('');
	let debouncedSearchQuery = $state('');
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

	// Filtered roasters based on search
	let filteredRoasters = $derived(
		searchQuery.trim() === ''
			? pageContext.roasters
			: pageContext.roasters.filter((roaster) =>
					roaster.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
					(roaster.location && roaster.location.toLowerCase().includes(searchQuery.toLowerCase()))
			  )
	);
</script>

<div class="mx-auto px-4 py-8 container">
	<!-- Breadcrumb Navigation -->
	<nav class="flex items-center gap-2 mb-6 text-gray-600 dark:text-cyan-400/70 text-sm">
		{#each pageContext.breadcrumbs as crumb, i}
			{#if i > 0}
				<ChevronRight class="w-4 h-4" />
			{/if}
			{#if crumb.href}
				<a href={crumb.href} class="hover:text-gray-900 dark:hover:text-cyan-200 transition-colors">
					{crumb.label}
				</a>
			{:else}
				<span class="font-medium text-gray-900 dark:text-cyan-100">{crumb.label}</span>
			{/if}
		{/each}
	</nav>

	<!-- Header Section -->
	<div class="bg-white dark:bg-slate-800/80 shadow-sm mb-8 p-8 border border-gray-200 dark:border-slate-700 rounded-xl">
		<div class="flex md:flex-row flex-col items-center gap-8 mb-8">
			{#if pageContext.countryCode}
				<div class="flex justify-center items-center bg-gray-50 dark:bg-slate-700/60 p-6 rounded-2xl w-32 md:w-48 h-32 md:h-48 shrink-0">
					<iconify-icon
						icon={`circle-flags:${pageContext.countryCode.toLowerCase()}`}
						style="font-size: 120px;"
					></iconify-icon>
				</div>
			{/if}
			<div class="md:text-left text-center">
				<h1 class="mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-6xl tracking-tight">
					Roasters in {pageContext.title}
				</h1>
			</div>
		</div>

		<!-- Statistics Grid -->
		<div class="gap-4 grid grid-cols-2 mx-auto mb-8">
			<a
				href={pageContext.locationCode ? `/search?roaster_location=${pageContext.locationCode}` : '/search'}
				class="group bg-gray-50 hover:bg-gray-100 dark:bg-slate-700/40 dark:hover:bg-slate-700/60 shadow-sm hover:shadow-md p-4 border border-gray-100 hover:border-gray-200 dark:border-slate-600 dark:hover:border-slate-500 rounded-xl text-center transition-all cursor-pointer"
			>
				<div class="relative flex justify-center items-center mb-2 min-h-[2.5rem] overflow-hidden">
					<span class="font-bold text-gray-900 dark:text-cyan-100 text-3xl transition-transform group-hover:-translate-x-3">
						{pageContext.statistics.total_beans.toLocaleString()}
					</span>
					<Search class="top-1/2 right-1/2 absolute opacity-0 group-hover:opacity-100 w-5 h-5 text-gray-600 dark:text-cyan-300 transition-all -translate-y-1/2 translate-x-1/2 group-hover:translate-x-12 duration-300" />
				</div>
				<div class="font-medium text-gray-500 dark:group-hover:text-cyan-300 dark:text-cyan-400/60 group-hover:text-gray-700 text-xs uppercase tracking-wider transition-colors">
					View Beans
				</div>
			</a>

			<div class="bg-gray-50 dark:bg-slate-700/40 p-4 border border-gray-100 dark:border-slate-600 rounded-xl text-center">
				<div class="mb-1 font-bold text-gray-900 dark:text-cyan-100 text-3xl">
					{pageContext.statistics.roaster_count}
				</div>
				<div class="font-medium text-gray-500 dark:text-cyan-400/60 text-xs uppercase tracking-wider">
					Roasters
				</div>
			</div>
		</div>

		<!-- Insights Section -->
		{#if pageContext.insights.originItems?.length || pageContext.insights.varietalItems?.length || pageContext.insights.cityItems?.length}
			<div class="gap-6 grid md:grid-cols-2">
				{#if pageContext.insights.originItems && pageContext.insights.originItems.length > 0}
					<InsightCard
						title="Popular Origins"
						icon={MapPin}
						items={pageContext.insights.originItems}
						variant="orange"
					/>
				{/if}

				{#if pageContext.insights.varietalItems && pageContext.insights.varietalItems.length > 0}
					<InsightCard
						title="Top Varietals"
						icon={Leaf}
						items={pageContext.insights.varietalItems}
						variant="blue"
					/>
				{/if}
			</div>
		{/if}
	</div>

	<!-- Page-specific extra content (like countries list for regions) -->
	{#if extraContent}
		{@render extraContent()}
	{/if}

	<!-- Roasters Section -->
	<div class="mb-12">
		<div class="flex md:flex-row flex-col justify-between md:items-end gap-6 mb-8">
			<!-- Search Bar -->
			<div class="relative mx-auto w-full max-w-md">
				<Search class="top-1/2 left-3 absolute w-4 h-4 text-gray-500 dark:text-cyan-400/70 -translate-y-1/2" />
				<input
					value={searchQuery}
					oninput={handleSearchInput}
					placeholder="Search roasters by name or location..."
					class="bg-white dark:bg-slate-700/60 px-3 py-2 pl-10 border border-gray-200 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 rounded-md outline-none focus:ring-1 focus:ring-orange-500 dark:focus:ring-emerald-500/50 w-full h-10 text-gray-900 dark:placeholder:text-cyan-400/70 dark:text-cyan-200 placeholder:text-gray-500 text-sm transition-all"
				/>
			</div>
		</div>

		<!-- View Toggle -->
		<div class="flex justify-center mb-8">
			<div class="justify-center justify-self-center items-center grid grid-cols-2 bg-gray-100 dark:bg-slate-700/60 p-1 border border-gray-200 dark:border-slate-600 rounded-lg w-fit">
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
			<div class="mb-4 text-gray-600 dark:text-cyan-400/80 text-sm text-right">
				{#if filteredRoasters.length === pageContext.roasters.length}
					{pageContext.roasters.length} roaster{pageContext.roasters.length === 1 ? '' : 's'}
				{:else}
					Showing {filteredRoasters.length} of {pageContext.roasters.length} roasters
				{/if}
			</div>

			{#if showStickerWall}
				<div in:fade={{ duration: 300 }}>
					<RoasterStickerWall roasters={filteredRoasters} debouncedSearchQuery={debouncedSearchQuery} />
				</div>
			{:else}
				<div class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4" in:fade={{ duration: 300 }}>
					{#each filteredRoasters as roaster, roaster_index (roaster.slug)}
						<div in:scale|global={{ delay: 50 * roaster_index }}>
							<RoasterCard {roaster} />
						</div>
					{/each}
				</div>
			{/if}
		{:else}
			<div class="py-20 border-2 border-gray-100 dark:border-slate-800 border-dashed rounded-2xl text-center">
				<Building2 class="mx-auto mb-4 w-12 h-12 text-gray-300 dark:text-slate-700" />
				<h3 class="mb-2 font-semibold text-gray-900 dark:text-cyan-100 text-xl">
					No roasters found
				</h3>
				<p class="text-gray-600 dark:text-cyan-400/70">
					No matching roasters found for "{searchQuery}".
				</p>
			</div>
		{/if}

		<!-- Empty State for search -->
		{#if filteredRoasters && filteredRoasters.length === 0 && searchQuery}
			<div class="py-12 text-center">
				<Button
					onclick={() => (searchQuery = "")}
					class="bg-orange-600 hover:bg-orange-700 dark:bg-emerald-600 dark:hover:bg-emerald-700 text-white"
					>Clear Search</Button
				>
			</div>
		{/if}
	</div>
</div>
