<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import type { PageData } from './$types';
	import CoffeeBeanCard from '$lib/components/CoffeeBeanCard.svelte';
	import PaginationControls from '$lib/components/PaginationControls.svelte';
	import SortControls from '$lib/components/SortControls.svelte';
	import { ArrowLeft, Users, MapPin, TrendingUp } from 'lucide-svelte';

	let { data }: { data: PageData } = $props();

	const varietal = $derived(data.varietal);
	const beans = $derived(data.beans);
	const pagination = $derived(data.pagination);
	const metadata = $derived(data.metadata);
	const queryParams = $derived(data.queryParams);

	// Update URL when sort/pagination changes
	function updateUrl(newParams: Record<string, string | number>) {
		const url = new URL($page.url);
		Object.entries(newParams).forEach(([key, value]) => {
			if (value) {
				url.searchParams.set(key, value.toString());
			} else {
				url.searchParams.delete(key);
			}
		});
		goto(url.toString(), { replaceState: true });
	}

	function handleSort(sortBy: string, sortOrder: string) {
		updateUrl({
			sort_by: sortBy,
			sort_order: sortOrder,
			page: 1 // Reset to first page when sorting
		});
	}

	function handlePageChange(newPage: number) {
		updateUrl({ page: newPage });
	}

	// Get varietal description based on category
	function getVarietalDescription(category: string): string {
		const descriptions: Record<string, string> = {
			typica: 'Typica is one of the oldest known coffee varieties, prized for its exceptional cup quality and complex flavor profiles. It forms the genetic foundation for many modern varieties and is known for producing clean, bright, and well-balanced coffees.',
			bourbon: 'Bourbon varieties are renowned for their sweet, wine-like characteristics and full body. They often produce complex cups with excellent balance, natural sweetness, and rich, fruity flavors that can range from chocolate to berry notes.',
			heirloom: 'Heirloom varieties are indigenous and wild coffee types that have evolved naturally in their native regions, particularly in Ethiopia. These varieties offer unique and unrepeatable flavor profiles that reflect their specific terroir and centuries of natural selection.',
			geisha: 'Geisha (or Gesha) is a highly prized variety known for its exceptional floral aromatics, jasmine-like characteristics, and clean, tea-like body. It produces coffees with extraordinary complexity, bright acidity, and distinctive tropical fruit flavors.',
			sl_varieties: 'SL varieties were developed by Scott Labs in Kenya and are bred for resistance to coffee diseases while maintaining exceptional cup quality. They typically produce coffees with bright acidity, wine-like characteristics, and complex fruit flavors.',
			hybrid: 'Hybrid varieties are modern cultivars bred for specific traits like disease resistance, productivity, and environmental adaptation. While maintaining quality characteristics, they offer improved resilience and often unique flavor profiles.',
			large_bean: 'Large bean varieties like Pacamara and Maragogype produce notably oversized beans that often result in unique cup characteristics. These varieties can offer distinctive flavors, lower acidity, and fuller body compared to standard-sized beans.',
			arabica_other: 'Other Arabica varieties represent the diverse range of coffee cultivars that have been developed for specific regional conditions or unique characteristics. Each offers its own distinct flavor profile and growing requirements.',
			other: 'Unique and specialty coffee varieties that don\'t fit into traditional categories, often representing regional innovations or rare cultivars with distinctive characteristics.'
		};
		return descriptions[category] || descriptions.other;
	}

	const varietalDescription = $derived(varietal ? getVarietalDescription(varietal.category) : '');
</script>

<svelte:head>
	<title>{varietal?.name || 'Varietal'} - Coffee Beans - Kissaten</title>
	<meta name="description" content="Explore {varietal?.statistics.total_beans || 0} coffee beans of the {varietal?.name || 'varietal'} variety. {varietalDescription.substring(0, 150)}..." />
</svelte:head>

<div class="mx-auto px-4 py-8 max-w-7xl container">
	<!-- Back Navigation -->
	<div class="mb-6">
		<a
			href="/varietals"
			class="inline-flex items-center font-medium text-orange-600 hover:text-orange-700 transition-colors"
		>
			<ArrowLeft class="mr-2 w-4 h-4" />
			Back to Coffee Varietals
		</a>
	</div>

	{#if varietal}
		<!-- Varietal Header -->
		<div class="bg-white mb-8 p-8 border border-gray-200 rounded-xl">
			<div class="mb-8 text-center">
				<h1 class="mb-4 font-bold text-gray-900 text-4xl md:text-5xl">
					{varietal.name}
				</h1>
				<div class="bg-orange-50 mx-auto mb-6 p-4 border border-orange-200 rounded-lg max-w-md">
					<p class="font-medium text-orange-800">
						{varietal.statistics.total_beans.toLocaleString()} coffee beans
					</p>
				</div>
			</div>

			<!-- Varietal Description -->
			<div class="mx-auto mb-8 max-w-4xl">
				<h2 class="mb-4 font-semibold text-gray-900 text-xl">About This Varietal</h2>
				<p class="text-gray-700 text-lg leading-relaxed">
					{varietalDescription}
				</p>
			</div>

			<!-- Statistics Grid -->
			<div class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 mb-8">
				<div class="bg-gray-50 p-4 rounded-lg text-center">
					<div class="font-bold text-gray-900 text-2xl">
						{varietal.statistics.total_beans.toLocaleString()}
					</div>
					<div class="text-gray-600 text-sm uppercase tracking-wide">Coffee Beans</div>
				</div>
				<div class="bg-gray-50 p-4 rounded-lg text-center">
					<div class="font-bold text-gray-900 text-2xl">
						{varietal.statistics.total_roasters}
					</div>
					<div class="text-gray-600 text-sm uppercase tracking-wide">Roasters</div>
				</div>
				<div class="bg-gray-50 p-4 rounded-lg text-center">
					<div class="font-bold text-gray-900 text-2xl">
						{varietal.statistics.total_countries}
					</div>
					<div class="text-gray-600 text-sm uppercase tracking-wide">Countries</div>
				</div>
				<div class="bg-gray-50 p-4 rounded-lg text-center">
					<div class="font-bold text-gray-900 text-2xl">
						{varietal.statistics.avg_price > 0 ? `€${varietal.statistics.avg_price.toFixed(2)}` : 'N/A'}
					</div>
					<div class="text-gray-600 text-sm uppercase tracking-wide">Avg Price</div>
				</div>
			</div>

			<!-- Insights Grid -->
			<div class="gap-6 grid md:grid-cols-2 lg:grid-cols-3">
				<!-- Top Countries -->
				<div class="bg-blue-50 p-6 border border-blue-200 rounded-lg">
					<div class="flex items-center mb-4">
						<MapPin class="mr-2 w-5 h-5 text-blue-600" />
						<h3 class="font-semibold text-blue-900">Popular Origins</h3>
					</div>
					<div class="space-y-2">
						{#each varietal.top_countries.slice(0, 5) as country}
							<div class="flex justify-between text-sm">
								<span class="text-blue-800">🌍 {country.country_name}</span>
								<span class="font-medium text-blue-900">{country.bean_count} beans</span>
							</div>
						{/each}
					</div>
				</div>

				<!-- Top Roasters -->
				<div class="bg-green-50 p-6 border border-green-200 rounded-lg">
					<div class="flex items-center mb-4">
						<Users class="mr-2 w-5 h-5 text-green-600" />
						<h3 class="font-semibold text-green-900">Top Roasters</h3>
					</div>
					<div class="space-y-2">
						{#each varietal.top_roasters.slice(0, 5) as roaster}
							<div class="flex justify-between text-sm">
								<span class="text-green-800 truncate">{roaster.name}</span>
								<span class="font-medium text-green-900">{roaster.bean_count} beans</span>
							</div>
						{/each}
					</div>
				</div>

				<!-- Common Tasting Notes -->
				<div class="bg-purple-50 p-6 border border-purple-200 rounded-lg">
					<div class="flex items-center mb-4">
						<TrendingUp class="mr-2 w-5 h-5 text-purple-600" />
						<h3 class="font-semibold text-purple-900">Common Flavors</h3>
					</div>
					<div class="space-y-2">
						{#each varietal.common_tasting_notes.slice(0, 6) as note}
							<div class="flex justify-between text-sm">
								<span class="text-purple-800">{note.note}</span>
								<span class="font-medium text-purple-900">{note.frequency}</span>
							</div>
						{/each}
					</div>
				</div>
			</div>
		</div>

		<!-- Coffee Beans Section -->
		<div class="bg-white p-6 border border-gray-200 rounded-xl">
			<!-- Section Header -->
			<div class="flex sm:flex-row flex-col sm:justify-between sm:items-center mb-6">
				<h2 class="mb-4 sm:mb-0 font-bold text-gray-900 text-2xl">
					Coffee Beans of {varietal.name} Varietal
				</h2>
				<SortControls
					currentSort={queryParams.sort_by}
					currentOrder={queryParams.sort_order}
					onSort={(e) => handleSort(e.sortBy, e.sortOrder)}
				/>
			</div>

			<!-- Coffee Beans Grid -->
			{#if beans && beans.length > 0}
				<div class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 mb-8">
					{#each beans as bean}
						<a href={"/roasters" + bean.bean_url_path} class="block">
							<CoffeeBeanCard {bean} />
						</a>
					{/each}
				</div>

				<!-- Pagination -->
				{#if pagination && pagination.total_pages > 1}
					<PaginationControls
						{pagination}
						onPageChange={(page) => handlePageChange(page)}
					/>
				{/if}
			{:else}
				<div class="py-12 text-center">
					<p class="text-gray-500">No coffee beans found for this varietal.</p>
				</div>
			{/if}
		</div>
	{:else}
		<!-- Error State -->
		<div class="bg-white p-8 border border-gray-200 rounded-xl text-center">
			<h1 class="mb-4 font-bold text-gray-900 text-2xl">Varietal Not Found</h1>
			<p class="mb-6 text-gray-600">
				{metadata?.error || 'The requested varietal could not be found.'}
			</p>
			<a
				href="/varietals"
				class="inline-flex items-center font-medium text-orange-600 hover:text-orange-700 transition-colors"
			>
				<ArrowLeft class="mr-2 w-4 h-4" />
				Back to Coffee Varietals
			</a>
		</div>
	{/if}
</div>
