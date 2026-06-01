<script lang="ts">
	import type { PageData } from "./$types";
	import GeographyBreadcrumb from "$lib/components/GeographyBreadcrumb.svelte";
	import ElevationMountainChart from "$lib/components/ElevationMountainChart.svelte";
	import {
		TrendingUp,
		Droplets,
		Leaf,
		Search,
	} from "lucide-svelte";
	import { getProcessIcon, normalizeFarmName } from "$lib/utils";
	import "iconify-icon";
	import UniversalOriginSearch from "$lib/components/UniversalOriginSearch.svelte";
	import type { OriginSearchResult } from "$lib/originsApi";

	import InsightCard from "$lib/components/InsightCard.svelte";

	let { data }: { data: PageData } = $props();
	const region = $derived(data.region);
	const farms = $derived(data.region.top_farms);

	let searchQuery = $state("");

	// Default results mapping summary farms to OriginSearchResult
	const defaultResults: OriginSearchResult[] = $derived(
		farms.map((f) => ({
			type: "farm" as const,
			name: f.farm_name,
			country_code: region.country_code,
			country_name: region.country_name,
			region_name: region.region_name,
			region_slug: data.regionSlug,
			farm_slug: normalizeFarmName(f.farm_name),
			producer_name: f.producer_name,
			bean_count: f.bean_count,
		})),
	);

	// Prepare items for InsightCard
	const varietalItems = $derived(
		region?.varietals?.slice(0, 5).map((v) => ({
			label: v.variety,
			count: v.count,
			href: `/search?variety="${encodeURIComponent(v.variety)}"&region=${encodeURIComponent(region.region_name)}&origin=${region.country_code}`,
		})) || [],
	);

	const processItems = $derived(
		region?.processing_methods
			?.filter((m) => !m.process.toLowerCase().includes("unknown"))
			.slice(0, 5)
			.map((m) => ({
				label: m.process,
				count: m.count,
				icon: getProcessIcon(m.process),
				href: `/search?process="${encodeURIComponent(m.process)}"&region=${encodeURIComponent(region.region_name)}&origin=${region.country_code}`,
			})) || [],
	);

	const noteItems = $derived(
		region?.common_tasting_notes?.slice(0, 5).map((n) => ({
			label: n.note,
			count: n.frequency,
			href: `/search?tasting_notes_query="${encodeURIComponent(n.note)}"&region=${encodeURIComponent(region.region_name)}&origin=${region.country_code}`,
		})) || [],
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
					class="group bg-gray-50 hover:bg-gray-100 dark:bg-slate-700/40 dark:hover:bg-slate-700/60 shadow-sm hover:shadow-md p-4 border border-gray-100 hover:border-gray-200 dark:border-slate-600 dark:hover:border-slate-500 rounded-xl text-center transition-all cursor-pointer"
				>
					<div class="relative flex justify-center items-center mb-2 min-h-[2.5rem] overflow-hidden">
						<span class="font-bold text-gray-900 dark:text-cyan-100 text-2xl transition-transform group-hover:-translate-x-3">
							{region.statistics.total_beans.toLocaleString()}
						</span>
						<Search class="top-1/2 right-1/2 absolute opacity-0 group-hover:opacity-100 w-4 h-4 text-gray-600 dark:text-cyan-300 transition-all -translate-y-1/2 translate-x-1/2 group-hover:translate-x-12 duration-300" />
					</div>
					<div
						class="font-medium text-gray-500 dark:group-hover:text-cyan-300 dark:text-cyan-400/60 group-hover:text-gray-700 text-xs uppercase tracking-wider transition-colors"
					>
						View Beans
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
				{#if varietalItems.length > 0}
					<InsightCard
						title="Common Varietals"
						icon={Leaf}
						items={varietalItems}
						variant="blue"
					/>
				{/if}

				<!-- Processing Methods -->
				{#if processItems.length > 0}
					<InsightCard
						title="Processing Methods"
						icon={Droplets}
						items={processItems}
						variant="orange"
					/>
				{/if}

				<!-- Common Tasting Notes -->
				{#if noteItems.length > 0}
					<InsightCard
						title="Common Tasting Notes"
						icon={TrendingUp}
						items={noteItems}
						variant="purple"
					/>
				{/if}
			</div>

			<!-- Elevation Chart -->
			{#if farms.length > 0 && farms.some(f => f.avg_elevation && f.avg_elevation > 0)}
				<div class="relative bg-white dark:bg-slate-800/80 shadow-sm mt-8 p-6 border border-gray-200 dark:border-slate-700 rounded-xl">
					<h3 class="top-6 left-6 z-10 absolute font-bold text-gray-900 dark:text-cyan-100 text-xl">
						Farm Elevation Distribution
					</h3>
					<ElevationMountainChart
						{farms}
						countryCode={region.country_code}
						regionSlug={data.regionSlug}
					/>
				</div>
			{/if}
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
						Explore farms in {region.region_name}
					</p>
				</div>
			</div>

			<UniversalOriginSearch
				{defaultResults}
				bind:searchQuery
				countryCode={region.country_code}
				regionSlug={data.regionSlug}
				placeholder="Search farms in this region..."
			/>
		</div>
	{/if}
</div>
