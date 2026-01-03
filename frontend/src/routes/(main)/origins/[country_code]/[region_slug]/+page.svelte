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
	} from "lucide-svelte";
	import { getProcessIcon } from "$lib/utils";
	import "iconify-icon";
	import { scale } from "svelte/transition";

	let { data }: { data: PageData } = $props();
	const region = $derived(data.region);
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
			class="bg-white dark:bg-slate-800/80 mb-8 p-8 border border-gray-200 dark:border-slate-700 rounded-xl shadow-sm"
		>
			<div class="flex items-start justify-between mb-8">
				<div>
					<div class="flex items-center gap-3 mb-2">
						<iconify-icon
							icon={`circle-flags:${region.country_code.toLowerCase()}`}
							class="text-2xl"
						></iconify-icon>
						<span
							class="text-gray-500 dark:text-cyan-400/70 font-medium uppercase tracking-wider text-sm"
							>{region.country_name}</span
						>
					</div>
					<h1
						class="font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl tracking-tight"
					>
						{region.region_name}
					</h1>
				</div>
				<div class="hidden md:flex flex-col items-end">
					<div
						class="bg-orange-100 dark:bg-emerald-500/20 text-orange-700 dark:text-emerald-300 px-4 py-2 rounded-full text-sm font-semibold"
					>
						Region Level Explorer
					</div>
				</div>
			</div>

			<!-- Quick Stats Grid -->
			<div class="gap-4 grid grid-cols-2 lg:grid-cols-4 mb-8">
				<div
					class="bg-gray-50 dark:bg-slate-700/40 p-4 border border-gray-100 dark:border-slate-600 rounded-xl text-center"
				>
					<div
						class="mb-1 font-bold text-gray-900 dark:text-cyan-100 text-2xl"
					>
						{region.statistics.total_beans.toLocaleString()}
					</div>
					<div
						class="text-gray-500 dark:text-cyan-400/60 text-xs uppercase tracking-wider"
					>
						Coffee Beans
					</div>
				</div>
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
					class="bg-emerald-50/50 dark:bg-emerald-900/20 p-5 rounded-xl border border-emerald-100 dark:border-emerald-800/50"
				>
					<div
						class="flex items-center gap-2 mb-4 text-emerald-600 dark:text-emerald-400"
					>
						<Grape class="w-5 h-5" />
						<h3
							class="font-semibold text-gray-900 dark:text-cyan-100"
						>
							Common Varietals
						</h3>
					</div>
					<div class="space-y-2">
						{#each region.varietals.slice(0, 5) as varietal}
							<div
								class="flex justify-between items-center text-sm"
							>
								<span class="text-gray-700 dark:text-cyan-200"
									>{varietal.variety}</span
								>
								<span
									class="font-medium text-gray-900 dark:text-cyan-100"
									>{varietal.count}</span
								>
							</div>
						{/each}
					</div>
				</div>

				<!-- Processing Methods -->
				<div
					class="bg-orange-50/50 dark:bg-orange-900/20 p-5 rounded-xl border border-orange-100 dark:border-orange-800/50"
				>
					<div
						class="flex items-center gap-2 mb-4 text-orange-600 dark:text-orange-400"
					>
						<Droplets class="w-5 h-5" />
						<h3
							class="font-semibold text-gray-900 dark:text-cyan-100"
						>
							Processing
						</h3>
					</div>
					<div class="space-y-2">
						{#each region.processing_methods.slice(0, 5) as method}
							{@const Icon = getProcessIcon(method.process)}
							<div
								class="flex justify-between items-center text-sm"
							>
								<span
									class="flex items-center gap-2 text-gray-700 dark:text-cyan-200"
								>
									<Icon class="w-3.5 h-3.5" />
									{method.process}
								</span>
								<span
									class="font-medium text-gray-900 dark:text-cyan-100"
									>{method.count}</span
								>
							</div>
						{/each}
					</div>
				</div>

				<!-- Flavour Profile -->
				<div
					class="bg-purple-50/50 dark:bg-purple-900/20 p-5 rounded-xl border border-purple-100 dark:border-purple-800/50"
				>
					<div
						class="flex items-center gap-2 mb-4 text-purple-600 dark:text-purple-400"
					>
						<TrendingUp class="w-5 h-5" />
						<h3
							class="font-semibold text-gray-900 dark:text-cyan-100"
						>
							Common Notes
						</h3>
					</div>
					<div class="space-y-2">
						{#each region.common_tasting_notes.slice(0, 5) as note}
							<div
								class="flex justify-between items-center text-sm"
							>
								<span class="text-gray-700 dark:text-cyan-200"
									>{note.note}</span
								>
								<span
									class="font-medium text-gray-900 dark:text-cyan-100"
									>{note.frequency}</span
								>
							</div>
						{/each}
					</div>
				</div>
			</div>
		</div>

		<!-- Farms Section -->
		<div class="mb-12">
			<div class="flex justify-between items-end mb-6">
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
				<a
					href={`/origins/${region.country_code}/${data.regionSlug}/farms`}
					class="flex items-center gap-1 font-medium text-orange-600 hover:text-orange-700 dark:text-emerald-400 dark:hover:text-emerald-300 transition-colors"
				>
					View All Farms <ArrowRight class="w-4 h-4" />
				</a>
			</div>

			<div class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
				{#each region.top_farms as farm, i}
					<div in:scale|global={{ delay: i * 50 }}>
						<FarmCard
							{farm}
							countryCode={region.country_code}
							regionSlug={data.regionSlug}
						/>
					</div>
				{/each}
			</div>
		</div>
	{/if}
</div>
