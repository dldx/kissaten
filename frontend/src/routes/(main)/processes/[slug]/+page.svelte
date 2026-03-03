<script lang="ts">
	import { page } from "$app/stores";
	import { goto } from "$app/navigation";
	import type { PageData } from "./$types";
	import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
	import PaginationControls from "$lib/components/PaginationControls.svelte";
	import SortControls from "$lib/components/SortControls.svelte";
	import BackButton from "$lib/components/BackButton.svelte";
	import { Users, MapPin, TrendingUp, Search } from "lucide-svelte";

	import { categoryConfig } from "$lib/config/process-categories";

	import InsightCard from "$lib/components/InsightCard.svelte";

	let { data }: { data: PageData } = $props();

	const process = $derived(data.process);
	const beans = $derived(data.beans);
	const pagination = $derived(data.pagination);
	const metadata = $derived(data.metadata);
	const queryParams = $derived(data.queryParams);

	// Prepare items for InsightCard
	const originItems = $derived(
		process?.top_countries?.slice(0, 6).map((c) => ({
			label: c.country_name,
			count: c.bean_count,
			countryCode: c.country_code,
			href: `/search?origin=${encodeURIComponent(c.country_code)}&process="${encodeURIComponent(process.name)}"`,
		})) || [],
	);

	const roasterItems = $derived(
		process?.top_roasters?.slice(0, 6).map((r) => ({
			label: r.name,
			count: r.bean_count,
			href: `/search?roaster=${encodeURIComponent(r.name)}&process="${encodeURIComponent(process.name)}"`,
		})) || [],
	);

	const noteItems = $derived(
		process?.common_tasting_notes?.slice(0, 6).map((n) => ({
			label: n.note,
			count: n.frequency,
			href: `/search?tasting_notes_query="${encodeURIComponent(n.note)}"&process="${encodeURIComponent(process.name)}"`,
		})) || [],
	);

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
		goto(url.toString(), { replaceState: true, noScroll: true });
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

	const processDescription = $derived(
		categoryConfig?.[process?.category]?.description ||
			categoryConfig?.other?.description ||
			"Information about this processing method.",
	);
</script>

<svelte:head>
	<title>{process.name} Process - Coffee Beans - Kissaten</title>
	<meta
		name="description"
		content="Explore {process.statistics
			.total_beans} coffee beans processed using the {process.name} method. {processDescription.substring(
			0,
			150,
		)}..."
	/>
</svelte:head>

<div class="mx-auto px-4 py-8 max-w-7xl container">
	<!-- Back Navigation -->
	<BackButton />

	<!-- Process Header -->
	<div
		class="bg-white dark:bg-slate-800/80 process-detail-card-shadow mb-8 p-8 border border-gray-200 rounded-xl"
	>
		<div class="mb-8 text-center">
			<h1
				class="process-detail-title-shadow mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl"
			>
				{process.name}
			</h1>
		</div>

		<!-- Process Description -->
		<div class="mx-auto mb-8 max-w-4xl">
			<h2
				class="process-detail-section-title-shadow mb-4 font-semibold text-gray-900 dark:text-emerald-300 text-xl"
			>
				About This Process
			</h2>
			<p
				class="process-detail-description-shadow text-gray-700 dark:text-cyan-200/90 text-lg leading-relaxed"
			>
				{processDescription}
			</p>
		</div>
		{#if process.original_names.length > 1}
			<div class="mx-auto mb-8 max-w-4xl">
				Other names: <p
					class="process-detail-description-shadow mt-2 text-gray-500 dark:text-cyan-400/70 text-sm italic"
				>
					{Array.from(
						new Set(
							process.original_names.map((d) =>
								d.name.toLowerCase(),
							),
						),
					).join(", ")}
				</p>
			</div>
		{/if}

		<!-- Statistics Grid -->
		<div class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 mb-8">
			<a
				href={`/search?process="${encodeURIComponent(process.name)}"`}
				class="group bg-gray-50 hover:bg-gray-100 dark:bg-slate-700/60 dark:hover:bg-slate-700/80 process-detail-stat-card-shadow shadow-sm hover:shadow-md p-4 dark:border dark:border-emerald-500/30 dark:hover:border-emerald-500/50 rounded-lg text-center transition-all cursor-pointer"
			>
				<div class="relative flex justify-center items-center mb-1 min-h-[2rem] overflow-hidden">
					<span class="process-detail-stat-shadow font-bold text-gray-900 dark:text-emerald-300 text-2xl transition-transform group-hover:-translate-x-3">
						{process.statistics.total_beans.toLocaleString()}
					</span>
					<Search class="top-1/2 right-1/2 absolute opacity-0 group-hover:opacity-100 w-4 h-4 text-gray-600 dark:text-emerald-300 transition-all -translate-y-1/2 translate-x-1/2 group-hover:translate-x-12 duration-300" />
				</div>
				<div
					class="process-detail-stat-label-shadow text-gray-500 dark:group-hover:text-cyan-300 dark:text-cyan-400/60 group-hover:text-gray-700 text-sm uppercase tracking-wide transition-colors"
				>
					View Beans
				</div>
			</a>
			<div
				class="bg-gray-50 dark:bg-slate-700/60 process-detail-stat-card-shadow p-4 dark:border dark:border-emerald-500/30 rounded-lg text-center"
			>
				<div
					class="process-detail-stat-shadow font-bold text-gray-900 dark:text-emerald-300 text-2xl"
				>
					{process.statistics.total_roasters}
				</div>
				<div
					class="process-detail-stat-label-shadow text-gray-600 dark:text-cyan-400/80 text-sm uppercase tracking-wide"
				>
					Roasters
				</div>
			</div>
			<div
				class="bg-gray-50 dark:bg-slate-700/60 process-detail-stat-card-shadow p-4 dark:border dark:border-emerald-500/30 rounded-lg text-center"
			>
				<div
					class="process-detail-stat-shadow font-bold text-gray-900 dark:text-emerald-300 text-2xl"
				>
					{process.statistics.total_countries}
				</div>
				<div
					class="process-detail-stat-label-shadow text-gray-600 dark:text-cyan-400/80 text-sm uppercase tracking-wide"
				>
					Countries
				</div>
			</div>
			<div
				class="bg-gray-50 dark:bg-slate-700/60 process-detail-stat-card-shadow p-4 dark:border dark:border-emerald-500/30 rounded-lg text-center"
			>
				<div
					class="process-detail-stat-shadow font-bold text-gray-900 dark:text-emerald-300 text-2xl"
				>
					{process.statistics.avg_price > 0
						? `${new Intl.NumberFormat("en-US", { style: "currency", currency: data.currencyState.selectedCurrency || "USD" }).format(process.statistics.avg_price)}`
						: "N/A"}
				</div>
				<div
					class="process-detail-stat-label-shadow text-gray-600 dark:text-cyan-400/80 text-sm uppercase tracking-wide"
				>
					Median Price/100g
				</div>
			</div>
		</div>
		<!-- Insights Grid -->
		<div class="gap-6 grid md:grid-cols-2 lg:grid-cols-3">
			<!-- Top Countries -->
			{#if originItems.length > 0}
				<InsightCard
					title="Popular Origins"
					icon={MapPin}
					items={originItems}
					variant="blue"
				/>
			{/if}

			<!-- Top Roasters -->
			{#if roasterItems.length > 0}
				<InsightCard
					title="Top Roasters"
					icon={Users}
					items={roasterItems}
					variant="green"
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
	</div>

	<!-- Coffee Beans Section -->
	<div
		class="bg-white dark:bg-slate-800/80 process-detail-card-shadow p-6 border border-gray-200 rounded-xl"
	>
		<!-- Section Header -->
		<div
			class="flex sm:flex-row flex-col sm:justify-between sm:items-center mb-6"
		>
			<h2
				class="process-detail-section-title-shadow mb-4 sm:mb-0 font-bold text-gray-900 dark:text-emerald-300 text-2xl"
			>
				Coffee Beans with {process.name} Process
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
				<p
					class="process-detail-description-shadow text-gray-500 dark:text-cyan-400/70"
				>
					No coffee beans found for this process.
				</p>
			</div>
		{/if}
	</div>
</div>
