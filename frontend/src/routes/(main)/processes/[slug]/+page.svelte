<script lang="ts">
	import { page } from "$app/stores";
	import { goto } from "$app/navigation";
	import type { PageData } from "./$types";
	import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
	import PaginationControls from "$lib/components/PaginationControls.svelte";
	import SortControls from "$lib/components/SortControls.svelte";
	import BackButton from "$lib/components/BackButton.svelte";
	import { Users, MapPin, TrendingUp } from "lucide-svelte";

	import { categoryConfig } from "$lib/config/process-categories";

	let { data }: { data: PageData } = $props();

	const process = $derived(data.process);
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
			<div
				class="bg-gray-50 dark:bg-slate-700/60 process-detail-stat-card-shadow p-4 dark:border dark:border-emerald-500/30 rounded-lg text-center"
			>
				<div
					class="process-detail-stat-shadow font-bold text-gray-900 dark:text-emerald-300 text-2xl"
				>
					{process.statistics.total_beans.toLocaleString()}
				</div>
				<div
					class="process-detail-stat-label-shadow text-gray-600 dark:text-cyan-400/80 text-sm uppercase tracking-wide"
				>
					Coffee Beans
				</div>
			</div>
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
						? `${new Intl.NumberFormat("en-US", { style: "currency", currency: data.currencyState.selectedCurrency }).format(process.statistics.avg_price)}`
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
			<div
				class="bg-blue-50 p-6 border border-blue-200 rounded-lg process-detail-insight-card-blue"
			>
				<div class="flex items-center mb-4">
					<MapPin
						class="process-detail-icon-shadow mr-2 w-5 h-5 text-blue-600 dark:text-cyan-400"
					/>
					<h3
						class="process-detail-insight-title-shadow font-semibold text-blue-900 dark:text-cyan-200"
					>
						Popular Origins
					</h3>
				</div>
				<div>
					{#each process.top_countries.slice(0, 6) as country}
						<a
							href={`/search?origin=${encodeURIComponent(country.country_code)}&process="${encodeURIComponent(process.name)}"`}
							class="flex justify-between hover:bg-accent p-1 px-2 text-sm"
						>
							<span
								class="process-detail-insight-item-shadow pr-4 text-blue-800 dark:text-cyan-300 truncate"
								><iconify-icon
									icon={`circle-flags:${country.country_code.toLowerCase()}`}
									inline
								></iconify-icon>
								{country.country_name}</span
							>
							<span
								class="process-detail-insight-item-shadow font-medium text-blue-900 dark:text-cyan-200"
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
				class="bg-green-50 p-6 border border-green-200 rounded-lg process-detail-insight-card-green"
			>
				<div class="flex items-center mb-4">
					<Users
						class="process-detail-icon-shadow mr-2 w-5 h-5 text-green-600 dark:text-emerald-400"
					/>
					<h3
						class="process-detail-insight-title-shadow font-semibold text-green-900 dark:text-emerald-200"
					>
						Top Roasters
					</h3>
				</div>
				<div>
					{#each process.top_roasters.slice(0, 6) as roaster}
						<a
							href={`/search?roaster=${encodeURIComponent(roaster.name)}&process="${encodeURIComponent(process.name)}"`}
							class="flex justify-between hover:bg-accent p-1 px-2 text-sm"
						>
							<span
								class="process-detail-roaster-name-shadow pr-4 text-green-800 dark:text-emerald-300 truncate"
								>{roaster.name}</span
							>
							<span
								class="process-detail-insight-item-shadow font-medium text-green-900 dark:text-emerald-200"
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
				class="bg-purple-50 p-6 border border-purple-200 rounded-lg process-detail-insight-card-purple"
			>
				<div class="flex items-center mb-4">
					<TrendingUp
						class="process-detail-icon-shadow mr-2 w-5 h-5 text-purple-600 dark:text-purple-400"
					/>
					<h3
						class="process-detail-insight-title-shadow font-semibold text-purple-900 dark:text-purple-200"
					>
						Common Tasting Notes
					</h3>
				</div>
				<div>
					{#each process.common_tasting_notes.slice(0, 6) as note}
						<a
							href={`/search?tasting_notes_query="${encodeURIComponent(note.note)}"&process="${encodeURIComponent(process.name)}"`}
							class="flex justify-between hover:bg-accent p-1 px-2 text-sm"
						>
							<span
								class="process-detail-tasting-note-shadow pr-4 text-purple-800 dark:text-purple-300 truncate"
								>{note.note}</span
							>
							<span
								class="process-detail-insight-item-shadow font-medium text-purple-900 dark:text-purple-200"
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
