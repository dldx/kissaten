<script lang="ts">
	import { page } from "$app/stores";
	import { goto } from "$app/navigation";
	import type { PageData } from "./$types";
	import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
	import PaginationControls from "$lib/components/PaginationControls.svelte";
	import SortControls from "$lib/components/SortControls.svelte";
	import BackButton from "$lib/components/BackButton.svelte";
	import { Users, MapPin, TrendingUp, Droplets } from "lucide-svelte";
	import { getProcessIcon } from "$lib/utils";
	import "iconify-icon";
	import ArrowLeft from "@lucide/svelte/icons/arrow-left";

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
		goto(url.toString(), { replaceState: true, noScroll: true }); // Prevent scrolling to top on URL change
	}

	function handleSort(sortBy: string, sortOrder: string) {
		updateUrl({
			sort_by: sortBy,
			sort_order: sortOrder,
			page: 1, // Reset to first page when sorting
		});
	}

	function handlePageChange(newPage: number) {
		updateUrl({ page: newPage });
	}

	// Get varietal description based on category
	function getVarietalDescription(category: string): string {
		const descriptions: Record<string, string> = {
			typica: "Typica is one of the oldest known coffee varieties, prized for its exceptional cup quality and complex flavour profiles. It forms the genetic foundation for many modern varieties and is known for producing clean, bright, and well-balanced coffees.",
			bourbon:
				"Bourbon varieties are renowned for their sweet, wine-like characteristics and full body. They often produce complex cups with excellent balance, natural sweetness, and rich, fruity flavours that can range from chocolate to berry notes.",
			heirloom:
				"Heirloom varieties are indigenous and wild coffee types that have evolved naturally in their native regions, particularly in Ethiopia. These varieties offer unique and unrepeatable flavour profiles that reflect their specific terroir and centuries of natural selection.",
			geisha: "Geisha (or Gesha) is a highly prized variety known for its exceptional floral aromatics, jasmine-like characteristics, and clean, tea-like body. It produces coffees with extraordinary complexity, bright acidity, and distinctive tropical fruit flavours.",
			sl_varieties:
				"SL varieties were developed by Scott Labs in Kenya and are bred for resistance to coffee diseases while maintaining exceptional cup quality. They typically produce coffees with bright acidity, wine-like characteristics, and complex fruit flavours.",
			hybrid: "Hybrid varieties are modern cultivars bred for specific traits like disease resistance, productivity, and environmental adaptation. While maintaining quality characteristics, they offer improved resilience and often unique flavour profiles.",
			large_bean:
				"Large bean varieties like Pacamara and Maragogype produce notably oversized beans that often result in unique cup characteristics. These varieties can offer distinctive flavours, lower acidity, and fuller body compared to standard-sized beans.",
			arabica_other:
				"Other Arabica varieties represent the diverse range of coffee cultivars that have been developed for specific regional conditions or unique characteristics. Each offers its own distinct flavour profile and growing requirements.",
			other: "Unique and specialty coffee varieties that don't fit into traditional categories, often representing regional innovations or rare cultivars with distinctive characteristics.",
		};
		return descriptions[category] || descriptions.other;
	}

	const varietalDescription = $derived(
		varietal ? getVarietalDescription(varietal.category) : "",
	);
</script>

<svelte:head>
	<title>{varietal?.name || "Varietal"} - Coffee Beans - Kissaten</title>
	<meta
		name="description"
		content="Explore {varietal?.statistics.total_beans ||
			0} coffee beans of the {varietal?.name ||
			'varietal'} variety. {varietalDescription.substring(0, 150)}..."
	/>
</svelte:head>

<div class="mx-auto px-4 py-8 max-w-7xl container">
	<!-- Back Navigation -->
	<BackButton />

	{#if varietal}
		<!-- Varietal Header -->
		<div
			class="bg-white dark:bg-slate-800/80 varietal-detail-card-shadow mb-8 p-8 border border-gray-200 rounded-xl"
		>
			<div class="mb-8 text-center">
				<h1
					class="varietal-detail-title-shadow mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl"
				>
					{varietal.name}
				</h1>
			</div>

			<!-- Varietal Description -->
			<div class="mx-auto mb-8 max-w-4xl">
				<h2
					class="varietal-detail-section-title-shadow mb-4 font-semibold text-gray-900 dark:text-emerald-300 text-xl"
				>
					About This Varietal
				</h2>
				<p
					class="varietal-detail-description-shadow text-gray-700 dark:text-cyan-200/90 text-lg leading-relaxed"
				>
					{varietalDescription}
				</p>
			</div>

			<!-- World Coffee Research Link -->
			{#if varietal.wcr_info && varietal.wcr_info.link}
				<div
					class="bg-gray-50 dark:bg-slate-700/40 mx-auto mb-8 p-6 border-emerald-500 dark:border-cyan-500 border-l-4 rounded-r-lg max-w-4xl"
				>
					{#if varietal.wcr_info.description}
						<p
							class="varietal-detail-description-shadow mb-3 text-gray-700 dark:text-cyan-200/80 text-base italic leading-relaxed"
						>
							"{varietal.wcr_info.description}"
						</p>
					{/if}
					<a
						href={varietal.wcr_info.link}
						target="_blank"
						rel="noopener noreferrer"
						class="inline-flex items-center gap-1.5 font-medium text-emerald-600 hover:text-emerald-700 dark:hover:text-cyan-300 dark:text-cyan-400 text-sm transition-colors"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							width="16"
							height="16"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<path
								d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"
							></path>
							<polyline points="15 3 21 3 21 9"></polyline>
							<line x1="10" y1="14" x2="21" y2="3"></line>
						</svg>
						Learn more on World Coffee Research
					</a>
				</div>
			{/if}

			{#if varietal.original_names && new Set(varietal.original_names.map( (d) => d.name.toLowerCase(), )).length > 1}
				<div class="mx-auto mb-8 max-w-4xl">
					Other names: <p
						class="varietal-detail-description-shadow mt-2 text-gray-500 dark:text-cyan-400/70 text-sm italic"
					>
						{Array.from(
							new Set(
								varietal.original_names.map((d) =>
									d.name.toLowerCase(),
								),
							),
						).join(", ")}
					</p>
				</div>
			{/if}
			<!-- Statistics Grid -->
			<div
				class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 mb-8"
			>
				<div
					class="bg-gray-50 dark:bg-slate-700/60 varietal-detail-stat-card-shadow p-4 dark:border dark:border-emerald-500/30 rounded-lg text-center"
				>
					<div
						class="varietal-detail-stat-shadow font-bold text-gray-900 dark:text-emerald-300 text-2xl"
					>
						{varietal.statistics.total_beans.toLocaleString()}
					</div>
					<div
						class="varietal-detail-stat-label-shadow text-gray-600 dark:text-cyan-400/80 text-sm uppercase tracking-wide"
					>
						Coffee Beans
					</div>
				</div>
				<div
					class="bg-gray-50 dark:bg-slate-700/60 varietal-detail-stat-card-shadow p-4 dark:border dark:border-emerald-500/30 rounded-lg text-center"
				>
					<div
						class="varietal-detail-stat-shadow font-bold text-gray-900 dark:text-emerald-300 text-2xl"
					>
						{varietal.statistics.total_roasters}
					</div>
					<div
						class="varietal-detail-stat-label-shadow text-gray-600 dark:text-cyan-400/80 text-sm uppercase tracking-wide"
					>
						Roasters
					</div>
				</div>
				<div
					class="bg-gray-50 dark:bg-slate-700/60 varietal-detail-stat-card-shadow p-4 dark:border dark:border-emerald-500/30 rounded-lg text-center"
				>
					<div
						class="varietal-detail-stat-shadow font-bold text-gray-900 dark:text-emerald-300 text-2xl"
					>
						{varietal.statistics.total_countries}
					</div>
					<div
						class="varietal-detail-stat-label-shadow text-gray-600 dark:text-cyan-400/80 text-sm uppercase tracking-wide"
					>
						Countries
					</div>
				</div>
				<div
					class="bg-gray-50 dark:bg-slate-700/60 varietal-detail-stat-card-shadow p-4 dark:border dark:border-emerald-500/30 rounded-lg text-center"
				>
					<div
						class="varietal-detail-stat-shadow font-bold text-gray-900 dark:text-emerald-300 text-2xl"
					>
						{varietal.statistics.avg_price > 0
							? `${new Intl.NumberFormat("en-US", { style: "currency", currency: data.currencyState.selectedCurrency || "USD" }).format(varietal.statistics.avg_price)}`
							: "N/A"}
					</div>
					<div
						class="varietal-detail-stat-label-shadow text-gray-600 dark:text-cyan-400/80 text-sm uppercase tracking-wide"
					>
						Median Price/100g
					</div>
				</div>
			</div>

			<!-- Insights Grid -->
			<div class="gap-6 grid md:grid-cols-2">
				<!-- Top Countries -->
				<div
					class="bg-gray-50 p-6 border border-blue-200 rounded-lg varietal-detail-insight-card-blue"
				>
					<div class="flex items-center mb-4">
						<MapPin
							class="mr-2 w-5 h-5 text-blue-600 dark:text-cyan-400"
						/>
						<h3
							class="varietal-detail-insight-title-shadow font-semibold text-blue-900 dark:text-cyan-200"
						>
							Popular Origins
						</h3>
					</div>
					<div>
						{#each varietal.top_countries.slice(0, 5) as country}
							<a
								href={`/search?origin=${encodeURIComponent(country.country_code)}&variety="${encodeURIComponent(varietal.name)}"`}
								class="flex justify-between hover:bg-accent p-1 px-2 text-sm"
							>
								<span
									class="varietal-detail-insight-item-shadow pr-4 text-blue-800 dark:text-cyan-300 truncate"
									><iconify-icon
										icon={`circle-flags:${country.country_code.toLowerCase()}`}
										inline
									></iconify-icon>
									{country.country_name}</span
								>
								<span
									class="varietal-detail-insight-item-shadow font-medium text-blue-900 dark:text-cyan-200"
									>{country.bean_count} bean{country.bean_count !==
									1
										? "s"
										: ""}</span
								>
							</a>
						{/each}
					</div>
				</div>

				<!-- Top Roasters -->
				<div
					class="bg-gray-50 p-6 border border-green-200 rounded-lg varietal-detail-insight-card-green"
				>
					<div class="flex items-center mb-4">
						<Users
							class="mr-2 w-5 h-5 text-green-600 dark:text-emerald-400"
						/>
						<h3
							class="varietal-detail-insight-title-shadow font-semibold text-green-900 dark:text-emerald-200"
						>
							Top Roasters
						</h3>
					</div>
					<div>
						{#each varietal.top_roasters.slice(0, 6) as roaster}
							<a
								href={`/search?roaster=${encodeURIComponent(roaster.name)}&variety="${encodeURIComponent(varietal.name)}"`}
								class="flex justify-between hover:bg-accent p-1 px-2 text-sm"
							>
								<span
									class="varietal-detail-insight-item-shadow pr-4 text-green-800 dark:text-emerald-300 truncate"
									>{roaster.name}</span
								>
								<span
									class="varietal-detail-insight-item-shadow font-medium text-green-900 dark:text-emerald-200"
									>{roaster.bean_count} bean{roaster.bean_count !==
									1
										? "s"
										: ""}</span
								>
							</a>
						{/each}
					</div>
				</div>

				<!-- Common Tasting Notes -->
				<div
					class="bg-gray-50 p-6 border border-purple-200 rounded-lg varietal-detail-insight-card-purple"
				>
					<div class="flex items-center mb-4">
						<TrendingUp
							class="mr-2 w-5 h-5 text-purple-600 dark:text-purple-400"
						/>
						<h3
							class="varietal-detail-insight-title-shadow font-semibold text-purple-900 dark:text-purple-200"
						>
							Common Tasting Notes
						</h3>
					</div>
					<div>
						{#each varietal.common_tasting_notes.slice(0, 6) as note}
							<a
								href={`/search?tasting_notes_query="${encodeURIComponent(note.note)}"&variety="${encodeURIComponent(varietal.name)}"`}
								class="flex justify-between hover:bg-accent p-1 px-2 text-sm"
							>
								<span
									class="varietal-detail-insight-item-shadow pr-4 text-purple-800 dark:text-purple-300"
									>{note.note}</span
								>
								<span
									class="varietal-detail-insight-item-shadow font-medium text-purple-900 dark:text-purple-200"
									>{note.frequency} bean{note.frequency !== 1
										? "s"
										: ""}</span
								>
							</a>
						{/each}
					</div>
				</div>

				<!-- Common Processing Methods -->
				{#if varietal.common_processing_methods && varietal.common_processing_methods.length > 0}
					<div
						class="bg-gray-50 p-6 border border-purple-200 rounded-lg varietal-detail-insight-card-purple"
					>
						<div class="flex items-center mb-4">
							<Droplets
								class="mr-2 w-5 h-5 text-orange-600 dark:text-orange-400"
							/>
							<h3
								class="varietal-detail-insight-title-shadow font-semibold text-orange-900 dark:text-orange-200"
							>
								Processing Methods
							</h3>
						</div>
						<div>
							{#each varietal.common_processing_methods.slice(0, 6) as process}
								{@const Icon = getProcessIcon(process.process)}
								<a
									href={`/search?process="${encodeURIComponent(process.process)}"&variety="${encodeURIComponent(varietal.name)}"`}
									class="flex justify-between items-center hover:bg-accent p-1 px-2 text-sm"
								>
									<span
										class="flex items-center varietal-detail-insight-item-shadow pr-4 text-orange-800 dark:text-orange-300 truncate-x"
									>
										<Icon class="mr-2 w-4 h-4 shrink-0"
										></Icon>
										{process.process}
									</span>
									<span
										class="varietal-detail-insight-item-shadow font-medium text-orange-900 dark:text-orange-200"
										>{process.frequency} bean{process.frequency !==
										1
											? "s"
											: ""}</span
									>
								</a>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		</div>

		<!-- Coffee Beans Section -->
		<div
			class="bg-white dark:bg-slate-800/80 varietal-detail-card-shadow p-6 border border-gray-200 rounded-xl"
		>
			<!-- Section Header -->
			<div
				class="flex sm:flex-row flex-col sm:justify-between sm:items-center mb-6"
			>
				<h2
					class="varietal-detail-section-title-shadow mb-4 sm:mb-0 font-bold text-gray-900 dark:text-emerald-300 text-2xl"
				>
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
				<div
					class="gap-4 sm:gap-6 grid grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 mb-8"
				>
					{#each beans as bean}
						<a
							href={"/roasters" + bean.bean_url_path}
							class="block"
						>
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
					<p
						class="varietal-detail-description-shadow text-gray-500 dark:text-cyan-400/70"
					>
						No coffee beans found for this varietal.
					</p>
				</div>
			{/if}
		</div>
	{:else}
		<!-- Error State -->
		<div
			class="bg-white dark:bg-slate-800/80 varietal-detail-card-shadow p-8 border border-gray-200 rounded-xl text-center"
		>
			<h1
				class="varietal-detail-title-shadow mb-4 font-bold text-gray-900 dark:text-cyan-100 text-2xl"
			>
				Varietal Not Found
			</h1>
			<p
				class="varietal-detail-description-shadow mb-6 text-gray-600 dark:text-cyan-300/80"
			>
				{metadata?.error ||
					"The requested varietal could not be found."}
			</p>
			<a
				href="/varietals"
				class="inline-flex items-center varietal-detail-back-link-shadow font-medium text-orange-600 hover:text-orange-700 dark:hover:text-orange-300 dark:text-orange-400 transition-colors"
			>
				<ArrowLeft class="mr-2 w-4 h-4" />
				Back to Coffee Varietals
			</a>
		</div>
	{/if}
</div>
