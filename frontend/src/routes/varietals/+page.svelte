<script lang="ts">
	import { page } from '$app/stores';
	import type { PageData } from './$types';
	import VarietalCategoryCard from '$lib/components/VarietalCategoryCard.svelte';

	let { data }: { data: PageData } = $props();

	const varietals = $derived(data.varietals);
	const metadata = $derived(data.metadata);

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

	// Sort categories by our defined order
	const sortedCategories = $derived(categoryOrder
		.map(categoryKey => ({ key: categoryKey, data: varietals[categoryKey] }))
		.filter(({ data }) => data && data.varietals.length > 0));

	// Calculate total beans across all categories
	const totalBeans = $derived(Object.values(varietals).reduce((sum, category) => sum + (category?.total_beans || 0), 0));
</script>

<svelte:head>
	<title>Coffee Varietals - Kissaten</title>
	<meta name="description" content="Explore different coffee varietals and their unique characteristics. From heritage Typica to exotic Geisha, discover the diversity of coffee varieties." />
</svelte:head>

<div class="mx-auto px-4 py-8 max-w-7xl container">
	<!-- Header -->
	<div class="mb-12 text-center">
		<h1 class="mb-4 font-bold text-gray-900 text-4xl md:text-5xl">
			Coffee Varietals
		</h1>
		<p class="mx-auto mb-6 max-w-3xl text-gray-600 text-xl">
			Discover the incredible diversity of coffee varietals, from heritage varieties that have been cultivated for centuries
			to modern hybrids bred for unique characteristics and environmental resilience.
		</p>
		<div class="bg-orange-50 mx-auto p-4 border border-orange-200 rounded-lg max-w-md">
			<p class="font-medium text-orange-800">
				{metadata?.total_varietals || 0} varietals
			</p>
		</div>
	</div>

	<!-- Varietal Categories Grid -->
	<div class="space-y-8">
		{#each sortedCategories as { key, data }}
			<VarietalCategoryCard
				categoryKey={key}
				category={data}
			/>
		{/each}
	</div>

	<!-- Additional Info Section -->
	<div class="bg-gray-50 mt-16 p-8 rounded-xl">
		<h2 class="mb-6 font-bold text-gray-900 text-2xl text-center">
			Understanding Coffee Varietals
		</h2>
		<div class="gap-6 grid md:grid-cols-2 lg:grid-cols-3 text-gray-700 text-sm">
			<div class="bg-white p-6 rounded-lg">
				<h3 class="mb-3 font-semibold text-gray-900">🌱 Typica Family</h3>
				<p>
					One of the oldest known varieties, Typica is prized for its exceptional cup quality
					and complex flavor profiles. It forms the genetic foundation for many modern varieties.
				</p>
			</div>
			<div class="bg-white p-6 rounded-lg">
				<h3 class="mb-3 font-semibold text-gray-900">🍇 Bourbon Family</h3>
				<p>
					Known for their sweet, wine-like characteristics and full body. Bourbon varieties
					often produce complex cups with excellent balance and natural sweetness.
				</p>
			</div>
			<div class="bg-white p-6 rounded-lg">
				<h3 class="mb-3 font-semibold text-gray-900">🏛️ Heirloom Varieties</h3>
				<p>
					Indigenous and wild varieties that have evolved naturally in their native regions,
					particularly Ethiopia, offering unique and unrepeatable flavor profiles.
				</p>
			</div>
			<div class="bg-white p-6 rounded-lg">
				<h3 class="mb-3 font-semibold text-gray-900">🌸 Geisha/Gesha</h3>
				<p>
					A highly prized variety known for its exceptional floral aromatics, jasmine-like
					characteristics, and clean, tea-like body with extraordinary complexity.
				</p>
			</div>
			<div class="bg-white p-6 rounded-lg">
				<h3 class="mb-3 font-semibold text-gray-900">🧬 Hybrid Varieties</h3>
				<p>
					Modern cultivars bred for specific traits like disease resistance, productivity,
					and environmental adaptation while maintaining quality characteristics.
				</p>
			</div>
			<div class="bg-white p-6 rounded-lg">
				<h3 class="mb-3 font-semibold text-gray-900">🔬 SL Varieties</h3>
				<p>
					Scott Labs selections developed in Kenya, bred for resistance to coffee diseases
					while producing exceptional cup quality with bright acidity and wine-like characteristics.
				</p>
			</div>
		</div>
	</div>
</div>
