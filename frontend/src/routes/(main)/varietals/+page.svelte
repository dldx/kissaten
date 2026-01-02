<script lang="ts">
	import { page } from "$app/stores";
	import type { PageData } from "./$types";
	import VarietalCategoryCard from "$lib/components/VarietalCategoryCard.svelte";
	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Search, Coffee, ArrowUp } from "lucide-svelte";
	import createFuzzySearch from "@nozbe/microfuzz";
	import { varietalConfig } from "$lib/config/varietal-categories";
	import * as Toc from "$lib/components/ui/toc";
	import { UseToc } from "$lib/hooks/use-toc.svelte";
	import { fly } from "svelte/transition";

	let { data }: { data: PageData } = $props();

	const varietals = $derived(data.varietals || {});
	const metadata = $derived(data.metadata);

	const toc = new UseToc();
	let showToc = $state(false);
	let understandingSection: HTMLElement;

	$effect(() => {
		if (!understandingSection) return;

		const observer = new IntersectionObserver(
			(entries) => {
				const entry = entries[0];
				showToc =
					!entry.isIntersecting && entry.boundingClientRect.top < 0;
			},
			{ threshold: 0 },
		);

		observer.observe(understandingSection);
		return () => observer.disconnect();
	});

	let searchQuery = $state("");

	// Define the order we want to display categories
	const categoryOrder = [
		"typica",
		"bourbon",
		"heirloom",
		"geisha",
		"sl_varieties",
		"hybrid",
		"large_bean",
		"arabica_other",
		"other",
	];

	// Filter individual varietals within categories based on search query
	const filteredCategories = $derived(
		categoryOrder
			.map((categoryKey) => {
				const categoryData = varietals[categoryKey];
				if (!categoryData || categoryData.varietals.length === 0)
					return null;

				if (!searchQuery.trim()) {
					return { key: categoryKey, data: categoryData };
				}

				// Create fuzzy search function for this category's varietals
				const fuzzySearch = createFuzzySearch(categoryData.varietals, {
					getText: (varietal) => [varietal.original_names],
				});

				// Get fuzzy search results
				const fuzzyResults = fuzzySearch(searchQuery);

				if (fuzzyResults.length === 0) return null;
				// Extract the matched processes (already sorted by score)
				const filteredVarietals = fuzzyResults.map(
					(result) => result.item,
				);
				// Create a new category data object with filtered varietals
				const filteredCategoryData = {
					...categoryData,
					varietals: filteredVarietals,
					total_beans: filteredVarietals.reduce(
						(sum, varietal) => sum + varietal.bean_count,
						0,
					),
				};

				return { key: categoryKey, data: filteredCategoryData };
			})
			.filter((item) => item !== null),
	);

	// Sort categories by our defined order
	const sortedCategories = $derived(filteredCategories);

	// Calculate total matching varietals
	const totalMatchingVarietals = $derived(
		sortedCategories.reduce(
			(sum, category) => sum + category.data.varietals.length,
			0,
		),
	);

	// Helper for display names
	function getCategoryName(key: string) {
		if (key === "sl_varieties") return "SL Varieties";
		if (key === "apiary") return "Apiary";
		return key
			.split("_")
			.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
			.join(" ");
	}
</script>

<svelte:head>
	<title>Coffee Varietals - Kissaten</title>
	<meta
		name="description"
		content="Explore different coffee varietals and their unique characteristics. From heritage Typica to exotic Geisha, discover the diversity of coffee varieties."
	/>
</svelte:head>

{#if showToc}
	<div
		transition:fly={{ x: 20, duration: 300 }}
		class="hidden xl:block top-24 right-8 z-50 fixed bg-background/95 supports-[backdrop-filter]:bg-background/80 shadow-lg backdrop-blur p-4 border rounded-lg w-64"
	>
		<Button
			variant="link"
			onclick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
			class="block p-0 hover:text-foreground hover:no-underline cursor-pointer"
			><ArrowUp class="inline w-4 h-4" />
			Back to top
		</Button>
		<Toc.Root toc={toc.current} />
	</div>
{/if}

<div class="mx-auto px-4 py-8 max-w-7xl container">
	<!-- Header -->
	<div class="mb-12 text-center" bind:this={understandingSection}>
		<h1
			class="varietal-title-shadow mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl"
		>
			Coffee Varietals
		</h1>
		<p
			class="varietal-description-shadow mx-auto mb-6 max-w-3xl text-gray-600 dark:text-cyan-300/80 text-xl"
		>
			Discover the incredible diversity of coffee varietals, from heritage
			varieties that have been cultivated for centuries to modern hybrids
			bred for unique characteristics and environmental resilience.
		</p>
		<!-- Understanding Section moved inside header wrapper for TOC trigger -->
		<div
			class="bg-gray-50 dark:bg-slate-800/60 varietal-info-card-shadow mt-16 p-8 dark:border dark:border-cyan-500/30 rounded-xl text-left"
		>
			<h2
				class="varietal-category-title-shadow mb-6 font-bold text-gray-900 dark:text-emerald-300 text-2xl text-center"
			>
				Understanding Coffee Varietals
			</h2>
			<div
				class="gap-6 grid md:grid-cols-2 lg:grid-cols-3 text-gray-700 dark:text-cyan-200/90 text-sm"
			>
				{#each categoryOrder as key}
					{@const config = varietalConfig[key]}
					<div
						class="bg-white dark:bg-slate-700/60 varietal-info-card-shadow p-6 dark:border dark:border-cyan-500/20 rounded-lg"
					>
						<h3
							class="varietal-info-title-shadow mb-3 font-semibold text-gray-900 dark:text-emerald-300"
						>
							{config.icon}
							{getCategoryName(key)}
						</h3>
						<p>
							{config.description}
						</p>
					</div>
				{/each}
			</div>
		</div>
	</div>

	<!-- Search Bar -->
	<div class="mx-auto mb-8 max-w-md">
		<div class="relative">
			<Search
				class="top-1/2 left-3 absolute w-4 h-4 text-gray-500 dark:text-cyan-400/70 -translate-y-1/2 transform"
			/>
			<Input
				bind:value={searchQuery}
				placeholder="Search varietals..."
				class="bg-white dark:bg-slate-700/60 pl-10 border-gray-200 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 focus:ring-orange-500 dark:focus:ring-emerald-500/50 text-gray-900 dark:placeholder:text-cyan-400/70 dark:text-cyan-200 placeholder:text-gray-500"
			/>
		</div>
	</div>

	<!-- Varietal Categories Grid -->
	{#if sortedCategories.length > 0}
		<div class="space-y-8" bind:this={toc.ref}>
			{#each sortedCategories as { key, data }}
				<VarietalCategoryCard categoryKey={key} category={data} />
			{/each}
		</div>

		<!-- Results Summary -->
		{#if searchQuery.trim()}
			<div class="mt-8 text-gray-600 dark:text-cyan-400/80 text-center">
				Showing {totalMatchingVarietals} matching varietals across {sortedCategories.length}
				categories
			</div>
		{/if}
	{:else if searchQuery.trim()}
		<!-- Empty State -->
		<div class="py-12 text-center">
			<Coffee
				class="mx-auto mb-4 w-12 h-12 text-muted-foreground dark:text-cyan-500/60"
			/>
			<h3
				class="varietal-title-shadow mb-2 font-semibold text-gray-900 dark:text-cyan-100 text-xl"
			>
				No varietals found
			</h3>
			<p
				class="varietal-description-shadow mb-4 text-muted-foreground dark:text-cyan-400/70"
			>
				Try searching with different keywords.
			</p>
			<Button onclick={() => (searchQuery = "")}>Clear Search</Button>
		</div>
	{/if}
</div>
