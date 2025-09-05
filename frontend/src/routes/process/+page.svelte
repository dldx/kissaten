<script lang="ts">
	import { page } from '$app/stores';
	import type { PageData } from './$types';
	import ProcessCategoryCard from '$lib/components/ProcessCategoryCard.svelte';
	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Search, Coffee } from "lucide-svelte";
	import createFuzzySearch from '@nozbe/microfuzz';

	let { data }: { data: PageData } = $props();

	const processes = $derived(data.processes);
	const metadata = $derived(data.metadata);

	let searchQuery = $state('');

	// Define the order we want to display categories
	const categoryOrder = [
		'washed',
		'natural',
		'anaerobic',
		'honey',
		'fermentation',
		'decaf',
		'experimental',
		'other'
	];

	// Filter individual processes within categories based on search query
	const filteredCategories = $derived(
		categoryOrder
			.map(categoryKey => {
				const categoryData = processes[categoryKey];
				if (!categoryData || categoryData.processes.length === 0) return null;

				if (!searchQuery.trim()) {
					return { key: categoryKey, data: categoryData };
				}

				// Create fuzzy search function for this category's processes
				const fuzzySearch = createFuzzySearch(categoryData.processes, {
					getText: (process) => [process.name]
				});

				// Get fuzzy search results
				const fuzzyResults = fuzzySearch(searchQuery);

				if (fuzzyResults.length === 0) return null;

				// Extract the matched processes (already sorted by score)
				const filteredProcesses = fuzzyResults.map(result => result.item);

				// Create a new category data object with filtered processes
				const filteredCategoryData = {
					...categoryData,
					processes: filteredProcesses,
					total_beans: filteredProcesses.reduce((sum, process) => sum + process.bean_count, 0)
				};

				return { key: categoryKey, data: filteredCategoryData };
			})
			.filter(item => item !== null)
	);

	// Sort categories by our defined order
	const sortedCategories = $derived(filteredCategories);

	// Calculate total matching processes
	const totalMatchingProcesses = $derived(
		sortedCategories.reduce((sum, category) => sum + category.data.processes.length, 0)
	);

	// Calculate total beans across all categories
	const totalBeans = $derived(Object.values(processes).reduce((sum, category) => sum + (category?.total_beans || 0), 0));
</script>

<svelte:head>
	<title>Coffee Processing Methods - Kissaten</title>
	<meta name="description" content="Explore different coffee processing methods and their impact on flavor profiles. From washed to natural, anaerobic to experimental processes." />
</svelte:head>

<div class="mx-auto px-4 py-8 max-w-7xl container">
	<!-- Header -->
	<div class="mb-12 text-center">
		<h1 class="process-title-shadow mb-4 font-bold text-gray-900 text-4xl md:text-5xl process-page-title-dark">
			Coffee Processing Methods
		</h1>
		<p class="process-description-shadow mx-auto mb-6 max-w-3xl text-gray-600 text-xl process-page-description-dark">
			Discover how different processing methods transform coffee cherries into the beans that create your favorite flavors.
			From traditional washed methods to innovative experimental processes.
		</p>
	</div>

	<!-- Search Bar -->
	<div class="mx-auto mb-8 max-w-md">
		<div class="relative">
			<Search class="top-1/2 left-3 absolute w-4 h-4 text-gray-500 dark:text-cyan-400/70 -translate-y-1/2 transform" />
			<Input
				bind:value={searchQuery}
				placeholder="Search processes..."
				class="bg-white dark:bg-slate-700/60 pl-10 border-gray-200 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 focus:ring-orange-500 dark:focus:ring-emerald-500/50 text-gray-900 dark:placeholder:text-cyan-400/70 dark:text-cyan-200 placeholder:text-gray-500"
			/>
		</div>
	</div>

	<!-- Process Categories Grid -->
	{#if sortedCategories.length > 0}
		<div class="space-y-8">
			{#each sortedCategories as { key, data }}
				<ProcessCategoryCard
					categoryKey={key}
					category={data}
				/>
			{/each}
		</div>

		<!-- Results Summary -->
		{#if searchQuery.trim()}
			<div class="mt-8 text-gray-600 dark:text-cyan-400/80 text-center">
				Showing {totalMatchingProcesses} matching processes across {sortedCategories.length} categories
			</div>
		{/if}
	{:else if searchQuery.trim()}
		<!-- Empty State -->
		<div class="py-12 text-center">
			<Coffee class="mx-auto mb-4 w-12 h-12 text-muted-foreground dark:text-cyan-500/60" />
			<h3 class="process-title-shadow mb-2 font-semibold text-gray-900 dark:text-cyan-100 text-xl">No processes found</h3>
			<p class="process-description-shadow mb-4 text-muted-foreground dark:text-cyan-400/70">Try searching with different keywords.</p>
			<Button onclick={() => searchQuery = ''}>Clear Search</Button>
		</div>
	{/if}

	<!-- Additional Info Section -->
	<div class="bg-gray-50 process-info-card-shadow mt-16 p-8 rounded-xl process-info-card-dark">
		<h2 class="process-category-title-shadow mb-6 font-bold text-gray-900 text-2xl text-center process-category-title-dark">
			Understanding Coffee Processing
		</h2>
		<div class="gap-6 grid md:grid-cols-2 lg:grid-cols-3 text-gray-700 text-sm">
			<div class="bg-white process-card-shadow p-6 rounded-lg process-card-dark">
				<h3 class="process-info-title-shadow mb-3 font-semibold text-gray-900 process-category-title-dark">🌊 Washed Process</h3>
				<p class="process-page-description-dark">
					Coffee cherries are pulped and fermented in water, then washed and dried.
					Results in clean, bright, and acidic flavor profiles with well-defined characteristics.
				</p>
			</div>
			<div class="bg-white process-card-shadow p-6 rounded-lg process-card-dark">
				<h3 class="process-info-title-shadow mb-3 font-semibold text-gray-900 process-category-title-dark">☀️ Natural Process</h3>
				<p class="process-page-description-dark">
					Whole coffee cherries are dried in the sun before removing the fruit.
					Creates fruity, wine-like flavors with more body and sweetness.
				</p>
			</div>
			<div class="bg-white process-card-shadow p-6 rounded-lg process-card-dark">
				<h3 class="process-info-title-shadow mb-3 font-semibold text-gray-900 process-category-title-dark">🫙 Anaerobic Process</h3>
				<p class="process-page-description-dark">
					Fermentation occurs in sealed, oxygen-free environments.
					Produces unique, complex flavors often described as funky or experimental.
				</p>
			</div>
			<div class="bg-white process-card-shadow p-6 rounded-lg process-card-dark">
				<h3 class="process-info-title-shadow mb-3 font-semibold text-gray-900 process-category-title-dark">🍯 Honey Process</h3>
				<p class="process-page-description-dark">
					Cherries are pulped but dried with some mucilage still attached.
					Balances the cleanliness of washed with the sweetness of natural.
				</p>
			</div>
			<div class="bg-white process-card-shadow p-6 rounded-lg process-card-dark">
				<h3 class="process-info-title-shadow mb-3 font-semibold text-gray-900 process-category-title-dark">🧪 Experimental</h3>
				<p class="process-page-description-dark">
					Innovative techniques like carbonic maceration, yeast inoculation, and thermal shock.
					Pushes the boundaries of flavor development.
				</p>
			</div>
			<div class="bg-white process-card-shadow p-6 rounded-lg process-card-dark">
				<h3 class="process-info-title-shadow mb-3 font-semibold text-gray-900 process-category-title-dark">🚫 Decaffeinated</h3>
				<p class="process-page-description-dark">
					Various methods to remove caffeine while preserving flavor, including
					Swiss Water, Ethyl Acetate, and Sugarcane processes.
				</p>
			</div>
		</div>
	</div>
</div>


