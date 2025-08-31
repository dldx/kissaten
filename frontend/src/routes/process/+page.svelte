<script lang="ts">
	import { page } from '$app/stores';
	import type { PageData } from './$types';
	import ProcessCategoryCard from '$lib/components/ProcessCategoryCard.svelte';

	let { data }: { data: PageData } = $props();

	const processes = $derived(data.processes);
	const metadata = $derived(data.metadata);

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

	// Sort categories by our defined order
	const sortedCategories = $derived(categoryOrder
		.map(categoryKey => ({ key: categoryKey, data: processes[categoryKey] }))
		.filter(({ data }) => data && data.processes.length > 0));

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
		<h1 class="mb-4 font-bold text-gray-900 text-4xl md:text-5xl">
			Coffee Processing Methods
		</h1>
		<p class="mx-auto mb-6 max-w-3xl text-gray-600 text-xl">
			Discover how different processing methods transform coffee cherries into the beans that create your favorite flavors.
			From traditional washed methods to innovative experimental processes.
		</p>
		<div class="bg-orange-50 mx-auto p-4 border border-orange-200 rounded-lg max-w-md">
			<p class="font-medium text-orange-800">
				{totalBeans.toLocaleString()} coffee beans across {metadata?.total_processes || 0} different processes
			</p>
		</div>
	</div>

	<!-- Process Categories Grid -->
	<div class="space-y-8">
		{#each sortedCategories as { key, data }}
			<ProcessCategoryCard
				categoryKey={key}
				category={data}
			/>
		{/each}
	</div>

	<!-- Additional Info Section -->
	<div class="bg-gray-50 mt-16 p-8 rounded-xl">
		<h2 class="mb-6 font-bold text-gray-900 text-2xl text-center">
			Understanding Coffee Processing
		</h2>
		<div class="gap-6 grid md:grid-cols-2 lg:grid-cols-3 text-gray-700 text-sm">
			<div class="bg-white p-6 rounded-lg">
				<h3 class="mb-3 font-semibold text-gray-900">🌊 Washed Process</h3>
				<p>
					Coffee cherries are pulped and fermented in water, then washed and dried.
					Results in clean, bright, and acidic flavor profiles with well-defined characteristics.
				</p>
			</div>
			<div class="bg-white p-6 rounded-lg">
				<h3 class="mb-3 font-semibold text-gray-900">☀️ Natural Process</h3>
				<p>
					Whole coffee cherries are dried in the sun before removing the fruit.
					Creates fruity, wine-like flavors with more body and sweetness.
				</p>
			</div>
			<div class="bg-white p-6 rounded-lg">
				<h3 class="mb-3 font-semibold text-gray-900">🫙 Anaerobic Process</h3>
				<p>
					Fermentation occurs in sealed, oxygen-free environments.
					Produces unique, complex flavors often described as funky or experimental.
				</p>
			</div>
			<div class="bg-white p-6 rounded-lg">
				<h3 class="mb-3 font-semibold text-gray-900">🍯 Honey Process</h3>
				<p>
					Cherries are pulped but dried with some mucilage still attached.
					Balances the cleanliness of washed with the sweetness of natural.
				</p>
			</div>
			<div class="bg-white p-6 rounded-lg">
				<h3 class="mb-3 font-semibold text-gray-900">🧪 Experimental</h3>
				<p>
					Innovative techniques like carbonic maceration, yeast inoculation, and thermal shock.
					Pushes the boundaries of flavor development.
				</p>
			</div>
			<div class="bg-white p-6 rounded-lg">
				<h3 class="mb-3 font-semibold text-gray-900">🚫 Decaffeinated</h3>
				<p>
					Various methods to remove caffeine while preserving flavor, including
					Swiss Water, Ethyl Acetate, and Sugarcane processes.
				</p>
			</div>
		</div>
	</div>
</div>


