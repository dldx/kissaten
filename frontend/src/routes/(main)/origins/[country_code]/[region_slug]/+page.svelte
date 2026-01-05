<script lang="ts">
	import type { PageData } from "./$types";
	import GeographyBreadcrumb from "$lib/components/GeographyBreadcrumb.svelte";
	import FarmCard from "$lib/components/FarmCard.svelte";
	import {
		Users,
		MapPin,
		TrendingUp,
		Droplets,
		ArrowRight,
		Coffee,
		Warehouse,
		ArrowUpCircle,
		Grape,
		Leaf,
	} from "lucide-svelte";
	import { getProcessIcon } from "$lib/utils";
	import { api } from "$lib/api";
	import "iconify-icon";
	import { scale } from "svelte/transition";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Search } from "lucide-svelte";

	let { data }: { data: PageData } = $props();
	const region = $derived(data.region);
	const farms = $derived(data.region.top_farms);

	let searchQuery = $state("");
	let filteredFarms = $derived(
		searchQuery.trim()
			? farms.filter((f) =>
					f.farm_name
						.toLowerCase()
						.includes(searchQuery.toLowerCase()),
				)
			: farms,
	);
</script>

<svelte:head>
	<title
		>{region?.region_name} ({region?.country_code}) - Coffee Origins -
		Kissaten</title
	>
</svelte:head>

<div class="mx-auto px-4 py-8 max-w-7xl container">
	<GeographyBreadcrumb
		countryCode={region?.country_code}
		countryName={region?.country_name}
		regionName={region?.region_name}
	/>

	{#if region}
		<!-- Header Section -->
		<div
			class="bg-white dark:bg-slate-800/80 shadow-sm mb-8 p-8 border border-gray-200 dark:border-slate-700 rounded-xl"
		>
			<div class="flex justify-between items-start mb-8">
				<div>
					<div class="flex items-center gap-3 mb-2">
						<iconify-icon
							icon={`circle-flags:${region.country_code.toLowerCase()}`}
							class="text-2xl"
						></iconify-icon>
						<span
							class="font-medium text-gray-500 dark:text-cyan-400/70 text-sm uppercase tracking-wider"
							>{region.country_name}</span
						>
					</div>
					<h1
						class="font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl tracking-tight"
					>
						{region.region_name}
					</h1>
					{#if !region.is_geocoded}
						<div
							class="flex items-center gap-2 mt-3 text-amber-600 dark:text-amber-400 text-sm"
						>
							<svg
								class="w-4 h-4"
								fill="currentColor"
								viewBox="0 0 20 20"
							>
								<path
									fill-rule="evenodd"
									d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
									clip-rule="evenodd"
								/>
							</svg>
							<span class="font-medium"
								>Unverified Region: This region hasn't been
								confirmed in our geographic database yet.</span
							>
						</div>
					{/if}
				</div>
				<div class="hidden md:flex flex-col items-end">
					<div
						class="bg-orange-100 dark:bg-emerald-500/20 px-4 py-2 rounded-full font-semibold text-orange-700 dark:text-emerald-300 text-sm"
					>
						Region
					</div>
				</div>
			</div>

			<!-- Quick Stats Grid -->
			<div class="gap-4 grid grid-cols-2 lg:grid-cols-4 mb-8">
				<a
					href={`/search?region=${encodeURIComponent(region.region_name)}&origin=${region.country_code}`}
					class="group bg-gray-50 hover:bg-gray-100 dark:bg-slate-700/40 dark:hover:bg-slate-700/60 p-4 border border-gray-100 dark:border-slate-600 rounded-xl text-center transition-colors"
				>
					<div
						class="mb-1 font-bold text-gray-900 dark:group-hover:text-emerald-400 dark:text-cyan-100 group-hover:text-orange-600 text-2xl transition-colors"
					>
						{region.statistics.total_beans.toLocaleString()}
					</div>
					<div
						class="text-gray-500 dark:text-cyan-400/60 text-xs uppercase tracking-wider"
					>
						Coffee Beans
					</div>
				</a>
				<div
					class="bg-gray-50 dark:bg-slate-700/40 p-4 border border-gray-100 dark:border-slate-600 rounded-xl text-center"
				>
					<div
						class="mb-1 font-bold text-gray-900 dark:text-cyan-100 text-2xl"
					>
						{region.statistics.total_roasters}
					</div>
					<div
						class="text-gray-500 dark:text-cyan-400/60 text-xs uppercase tracking-wider"
					>
						Roasters
					</div>
				</div>
				<div
					class="bg-gray-50 dark:bg-slate-700/40 p-4 border border-gray-100 dark:border-slate-600 rounded-xl text-center"
				>
					<div
						class="mb-1 font-bold text-gray-900 dark:text-cyan-100 text-2xl"
					>
						{region.statistics.total_farms}
					</div>
					<div
						class="text-gray-500 dark:text-cyan-400/60 text-xs uppercase tracking-wider"
					>
						Known Farms
					</div>
				</div>
				<div
					class="bg-gray-50 dark:bg-slate-700/40 p-4 border border-gray-100 dark:border-slate-600 rounded-xl text-center"
				>
					<div
						class="mb-1 font-bold text-gray-900 dark:text-cyan-100 text-2xl"
					>
						{region.elevation_range.avg
							? `${Math.round(region.elevation_range.avg)}m`
							: "N/A"}
					</div>
					<div
						class="text-gray-500 dark:text-cyan-400/60 text-xs uppercase tracking-wider"
					>
						Avg Elevation
					</div>
				</div>
			</div>

			<!-- Insights Grid -->
			<div class="gap-6 grid md:grid-cols-3">
				<!-- Top Varietals -->
				<div
					class="bg-gray-50 p-6 border border-blue-200 rounded-lg varietal-detail-insight-card-blue"
				>
					<div
						class="flex items-center gap-2 mb-4 text-blue-600 dark:text-cyan-400"
					>
						<Leaf class="w-5 h-5" />
						<h3
							class="varietal-detail-insight-title-shadow font-semibold text-blue-900 dark:text-cyan-200"
						>
							Common Varietals
						</h3>
					</div>
					<div class="space-y-1">
						{#each region.varietals.slice(0, 5) as varietal}
							<a
								href={`/search?variety=${encodeURIComponent(varietal.variety)}&region=${encodeURIComponent(region.region_name)}&country=${region.country_code}`}
								class="flex justify-between items-center hover:bg-accent p-1 px-2 rounded text-sm transition-colors"
							>
								<span
									class="varietal-detail-insight-item-shadow text-emerald-800 dark:text-emerald-300 truncate"
									>{varietal.variety}</span
								>
								<span
									class="varietal-detail-insight-item-shadow font-medium text-emerald-900 dark:text-emerald-200"
									>{varietal.count} bean{varietal.count !== 1
										? "s"
										: ""}</span
								>
							</a>
						{/each}
					</div>
				</div>

				<!-- Processing Methods -->
				<div
					class="bg-gray-50 p-6 border border-orange-200 rounded-lg varietal-detail-insight-card-orange"
				>
					<div
						class="flex items-center gap-2 mb-4 text-orange-600 dark:text-orange-400"
					>
						<Droplets class="w-5 h-5" />
						<h3
							class="varietal-detail-insight-title-shadow font-semibold text-orange-900 dark:text-orange-200"
						>
							Processing Methods
						</h3>
					</div>
					<div class="space-y-1">
						{#each region.processing_methods
							.filter((method) => !method.process
										.toLowerCase()
										.includes("unknown"))
							.slice(0, 5) as method}
							{@const Icon = getProcessIcon(method.process)}
							<a
								href={`/search?process=${encodeURIComponent(method.process)}&region=${encodeURIComponent(region.region_name)}&country=${region.country_code}`}
								class="flex justify-between items-center hover:bg-accent p-1 px-2 rounded text-sm transition-colors"
							>
								<span
									class="flex items-center gap-2 varietal-detail-insight-item-shadow text-orange-800 dark:text-orange-300 truncate"
								>
									<Icon class="w-3.5 h-3.5" />
									{method.process}
								</span>
								<span
									class="varietal-detail-insight-item-shadow font-medium text-orange-900 dark:text-orange-200"
									>{method.count} bean{method.count !== 1
										? "s"
										: ""}</span
								>
							</a>
						{/each}
					</div>
				</div>

				<!-- Flavour Profile -->
				<div
					class="bg-gray-50 p-6 border border-purple-200 rounded-lg varietal-detail-insight-card-purple"
				>
					<div
						class="flex items-center gap-2 mb-4 text-purple-600 dark:text-purple-400"
					>
						<TrendingUp class="w-5 h-5" />
						<h3
							class="varietal-detail-insight-title-shadow font-semibold text-purple-900 dark:text-purple-200"
						>
							Common Tasting Notes
						</h3>
					</div>
					<div class="space-y-1">
						{#each region.common_tasting_notes.slice(0, 5) as note}
							<a
								href={`/search?tasting_notes_query="${encodeURIComponent(note.note)}"&region=${encodeURIComponent(region.region_name)}&country=${region.country_code}`}
								class="flex justify-between items-center hover:bg-accent p-1 px-2 rounded text-sm transition-colors"
							>
								<span
									class="varietal-detail-insight-item-shadow text-purple-800 dark:text-purple-300 truncate"
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
			</div>
		</div>

		<!-- Farms Section -->
		<div class="mb-12">
			<div
				class="flex md:flex-row flex-col justify-between md:items-end gap-6 mb-8"
			>
				<div>
					<h2
						class="font-bold text-gray-900 dark:text-cyan-100 text-3xl"
					>
						Coffee Farms
					</h2>
					<p class="mt-1 text-gray-600 dark:text-cyan-400/80">
						Explore {region.statistics.total_farms} farms in {region.region_name}
					</p>
				</div>

				<!-- Search Bar -->
				<div class="relative w-full max-w-md">
					<Search
						class="top-1/2 left-3 absolute w-4 h-4 text-gray-500 dark:text-cyan-400/70 -translate-y-1/2"
					/>
					<Input
						bind:value={searchQuery}
						placeholder="Search farms in this region..."
						class="bg-white dark:bg-slate-700/60 pl-10 border-gray-200 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 focus:ring-orange-500 dark:focus:ring-emerald-500/50 text-gray-900 dark:text-cyan-200"
					/>
				</div>
			</div>

			{#if filteredFarms.length > 0}
				<div
					class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
				>
					{#each filteredFarms as farm, i (farm.farm_name)}
						<div in:scale|global={{ delay: (i % 20) * 30 }}>
							<FarmCard
								{farm}
								countryCode={region.country_code}
								regionSlug={data.regionSlug}
							/>
						</div>
					{/each}
				</div>
			{:else}
				<div
					class="py-20 border-2 border-gray-100 dark:border-slate-800 border-dashed rounded-2xl text-center"
				>
					<Warehouse
						class="mx-auto mb-4 w-12 h-12 text-gray-300 dark:text-slate-700"
					/>
					<h3
						class="mb-2 font-semibold text-gray-900 dark:text-cyan-100 text-xl"
					>
						No farms found
					</h3>
					<p class="text-gray-600 dark:text-cyan-400/70">
						No matching coffee farms found for "{searchQuery}".
					</p>
				</div>
			{/if}
		</div>
	{/if}
</div>
