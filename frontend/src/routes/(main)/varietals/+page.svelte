<script lang="ts">
	import { page } from '$app/stores';
	import type { PageData } from './$types';
	import VarietalCategoryCard from '$lib/components/VarietalCategoryCard.svelte';
	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Search, Coffee } from "lucide-svelte";
	import createFuzzySearch from '@nozbe/microfuzz';

	let { data }: { data: PageData } = $props();

	const varietals = $derived(data.varietals);
	const metadata = $derived(data.metadata);

	let searchQuery = $state('');

	// Define the order we want to display categories
	const categoryOrder = [
		'typica',
		'bourbon',
		'heirloom',
		'geisha',
		'sl_varieties',
		'hybrid',
		'large_bean',
		'arabica_other',
		'other'
	];

	// Filter individual varietals within categories based on search query
	const filteredCategories = $derived(
		categoryOrder
			.map(categoryKey => {
				const categoryData = varietals[categoryKey];
				if (!categoryData || categoryData.varietals.length === 0) return null;

				if (!searchQuery.trim()) {
					return { key: categoryKey, data: categoryData };
				}

				// Create fuzzy search function for this category's varietals
				const fuzzySearch = createFuzzySearch(categoryData.varietals, {
					getText: (varietal) => [varietal.name]
				});

				// Get fuzzy search results
				const fuzzyResults = fuzzySearch(searchQuery);

				if (fuzzyResults.length === 0) return null;

				// Extract the matched varietals (already sorted by score)
				const filteredVarietals = fuzzyResults.map(result => result.item);

				// Create a new category data object with filtered varietals
				const filteredCategoryData = {
					...categoryData,
					varietals: filteredVarietals,
					total_beans: filteredVarietals.reduce((sum, varietal) => sum + varietal.bean_count, 0)
				};

				return { key: categoryKey, data: filteredCategoryData };
			})
			.filter(item => item !== null)
	);

	// Sort categories by our defined order
	const sortedCategories = $derived(filteredCategories);

	// Calculate total matching varietals
	const totalMatchingVarietals = $derived(
		sortedCategories.reduce((sum, category) => sum + category.data.varietals.length, 0)
	);

</script>

<svelte:head>
	<title>Coffee Varietals - Kissaten</title>
	<meta name="description" content="Explore different coffee varietals and their unique characteristics. From heritage Typica to exotic Geisha, discover the diversity of coffee varieties." />
</svelte:head>

<div class="mx-auto px-4 py-8 max-w-7xl container">
	<!-- Header -->
	<div class="mb-12 text-center">
		<h1 class="varietal-title-shadow mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl">Coffee Varietals</h1>
		<p class="varietal-description-shadow mx-auto mb-6 max-w-3xl text-gray-600 dark:text-cyan-300/80 text-xl">
			Discover the incredible diversity of coffee varietals, from heritage varieties that have been cultivated for centuries
			to modern hybrids bred for unique characteristics and environmental resilience.
		</p>
	</div>

	<!-- Search Bar -->
	<div class="mx-auto mb-8 max-w-md">
		<div class="relative">
			<Search class="top-1/2 left-3 absolute w-4 h-4 text-gray-500 dark:text-cyan-400/70 -translate-y-1/2 transform" />
			<Input
				bind:value={searchQuery}
				placeholder="Search varietals..."
				class="bg-white dark:bg-slate-700/60 pl-10 border-gray-200 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 focus:ring-orange-500 dark:focus:ring-emerald-500/50 text-gray-900 dark:placeholder:text-cyan-400/70 dark:text-cyan-200 placeholder:text-gray-500"
			/>
		</div>
	</div>

	<!-- Varietal Categories Grid -->
	{#if sortedCategories.length > 0}
		<div class="space-y-8">
			{#each sortedCategories as { key, data }}
				<VarietalCategoryCard
					categoryKey={key}
					category={data}
				/>
			{/each}
		</div>

		<!-- Results Summary -->
		{#if searchQuery.trim()}
			<div class="mt-8 text-gray-600 dark:text-cyan-400/80 text-center">
				Showing {totalMatchingVarietals} matching varietals across {sortedCategories.length} categories
			</div>
		{/if}
	{:else if searchQuery.trim()}
		<!-- Empty State -->
		<div class="py-12 text-center">
			<Coffee class="mx-auto mb-4 w-12 h-12 text-muted-foreground dark:text-cyan-500/60" />
			<h3 class="varietal-title-shadow mb-2 font-semibold text-gray-900 dark:text-cyan-100 text-xl">No varietals found</h3>
			<p class="varietal-description-shadow mb-4 text-muted-foreground dark:text-cyan-400/70">Try searching with different keywords.</p>
			<Button onclick={() => searchQuery = ''}>Clear Search</Button>
		</div>
	{/if}

	<!-- Additional Info Section -->
	<div class="bg-gray-50 dark:bg-slate-800/60 varietal-info-card-shadow mt-16 p-8 dark:border dark:border-cyan-500/30 rounded-xl">
		<h2 class="varietal-category-title-shadow mb-6 font-bold text-gray-900 dark:text-emerald-300 text-2xl text-center">
			Understanding Coffee Varietals
		</h2>
		<div class="gap-6 grid md:grid-cols-2 lg:grid-cols-3 text-gray-700 dark:text-cyan-200/90 text-sm">
			<div class="bg-white dark:bg-slate-700/60 varietal-info-card-shadow p-6 dark:border dark:border-cyan-500/20 rounded-lg">
				<h3 class="varietal-info-title-shadow mb-3 font-semibold text-gray-900 dark:text-emerald-300">🌱 Typica Family</h3>
				<p>
					One of the oldest known varieties, Typica is prized for its exceptional cup quality
					and complex flavor profiles. It forms the genetic foundation for many modern varieties.
				</p>
			</div>
			<div class="bg-white dark:bg-slate-700/60 varietal-info-card-shadow p-6 dark:border dark:border-cyan-500/20 rounded-lg">
				<h3 class="varietal-info-title-shadow mb-3 font-semibold text-gray-900 dark:text-emerald-300">🍇 Bourbon Family</h3>
				<p>
					Known for their sweet, wine-like characteristics and full body. Bourbon varieties
					often produce complex cups with excellent balance and natural sweetness.
				</p>
			</div>
			<div class="bg-white dark:bg-slate-700/60 varietal-info-card-shadow p-6 dark:border dark:border-cyan-500/20 rounded-lg">
				<h3 class="varietal-info-title-shadow mb-3 font-semibold text-gray-900 dark:text-emerald-300">🏛️ Heirloom Varieties</h3>
				<p>
					Indigenous and wild varieties that have evolved naturally in their native regions,
					particularly Ethiopia, offering unique and unrepeatable flavor profiles.
				</p>
			</div>
			<div class="bg-white dark:bg-slate-700/60 varietal-info-card-shadow p-6 dark:border dark:border-cyan-500/20 rounded-lg">
				<h3 class="varietal-info-title-shadow mb-3 font-semibold text-gray-900 dark:text-emerald-300">🌸 Geisha/Gesha</h3>
				<p>
					A highly prized variety known for its exceptional floral aromatics, jasmine-like
					characteristics, and clean, tea-like body with extraordinary complexity.
				</p>
			</div>
			<div class="bg-white dark:bg-slate-700/60 varietal-info-card-shadow p-6 dark:border dark:border-cyan-500/20 rounded-lg">
				<h3 class="varietal-info-title-shadow mb-3 font-semibold text-gray-900 dark:text-emerald-300">🧬 Hybrid Varieties</h3>
				<p>
					Modern cultivars bred for specific traits like disease resistance, productivity,
					and environmental adaptation while maintaining quality characteristics.
				</p>
			</div>
			<div class="bg-white dark:bg-slate-700/60 varietal-info-card-shadow p-6 dark:border dark:border-cyan-500/20 rounded-lg">
				<h3 class="varietal-info-title-shadow mb-3 font-semibold text-gray-900 dark:text-emerald-300">🔬 SL Varieties</h3>
				<p>
					Scott Labs selections developed in Kenya, bred for resistance to coffee diseases
					while producing exceptional cup quality with bright acidity and wine-like characteristics.
				</p>
			</div>
		</div>
	</div>
</div>
