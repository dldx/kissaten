<script lang="ts">
	import { page } from "$app/stores";
	import type { PageData } from "./$types";
	import ProcessCategoryCard from "$lib/components/ProcessCategoryCard.svelte";
	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Search, Coffee, ArrowUp } from "lucide-svelte";
	import createFuzzySearch from "@nozbe/microfuzz";
	import { categoryConfig } from "$lib/config/process-categories";

	let { data }: { data: PageData } = $props();

	const processes = $derived(data.processes);
	const metadata = $derived(data.metadata);

	let searchQuery = $state("");

	// Define the order we want to display categories
	const categoryOrder = [
		"washed",
		"natural",
		"anaerobic",
		"honey",
		"fermentation",
		"decaf",
		"experimental",
		"other",
	];

	// Filter individual processes within categories based on search query
	const filteredCategories = $derived(
		categoryOrder
			.map((categoryKey) => {
				const categoryData = processes[categoryKey];
				if (!categoryData || categoryData.processes.length === 0)
					return null;

				if (!searchQuery.trim()) {
					return { key: categoryKey, data: categoryData };
				}

				// Create fuzzy search function for this category's processes
				const fuzzySearch = createFuzzySearch(categoryData.processes, {
					getText: (process: Process) => [process.original_names],
				});

				// Get fuzzy search results
				const fuzzyResults = fuzzySearch(searchQuery);

				if (fuzzyResults.length === 0) return null;

				// Extract the matched processes (already sorted by score)
				const filteredProcesses = fuzzyResults.map(
					(result) => result.item,
				);

				// Create a new category data object with filtered processes
				const filteredCategoryData = {
					...categoryData,
					processes: filteredProcesses,
					total_beans: filteredProcesses.reduce(
						(sum, process) => sum + process.bean_count,
						0,
					),
				};

				return { key: categoryKey, data: filteredCategoryData };
			})
			.filter((item) => item !== null),
	);

	// Sort categories by our defined order
	const sortedCategories = $derived(filteredCategories);

	// Calculate total matching processes
	const totalMatchingProcesses = $derived(
		sortedCategories.reduce(
			(sum, category) => sum + category.data.processes.length,
			0,
		),
	);

	let showToc = $state(false);
	let understandingSection: HTMLElement;

	$effect(() => {
		if (!understandingSection) return;

		const observer = new IntersectionObserver(
			(entries) => {
				const entry = entries[0];
				// Show TOC when the understanding section is no longer intersecting (scrolled past)
				// and we are below the top of the page (boundingClientRect.top < 0)
				showToc =
					!entry.isIntersecting && entry.boundingClientRect.top < 0;
			},
			{ threshold: 0 },
		);

		observer.observe(understandingSection);

		return () => observer.disconnect();
	});

	import * as Toc from "$lib/components/ui/toc";
	import { UseToc } from "$lib/hooks/use-toc.svelte";
	import { fly } from "svelte/transition";
    import type { Process } from "$lib/api";
	const toc = new UseToc();
</script>

<svelte:head>
	<title>Coffee Processing Methods - Kissaten</title>
	<meta
		name="description"
		content="Explore different coffee processing methods and their impact on flavour profiles. From washed to natural, anaerobic to experimental processes."
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
			class="process-title-shadow mb-4 font-bold text-gray-900 text-4xl md:text-5xl process-page-title-dark"
		>
			Coffee Processing Methods
		</h1>
		<p
			class="process-description-shadow mx-auto mb-6 max-w-3xl text-gray-600 text-xl process-page-description-dark"
		>
			Discover how different processing methods transform coffee cherries
			into the beans that create your favorite flavours. From traditional
			washed methods to innovative experimental processes.
		</p>
		<h2
			class="process-category-title-shadow mb-6 font-bold text-gray-900 text-2xl text-center process-category-title-dark"
		>
			Understanding Coffee Processing
		</h2>
		<div
			class="gap-6 grid md:grid-cols-2 lg:grid-cols-3 text-gray-700 text-sm"
		>
			{#each categoryOrder as key}
				{@const config = categoryConfig[key]}
				<div
					class="bg-white process-card-shadow p-6 rounded-lg process-card-dark"
				>
					<h3
						class="process-info-title-shadow mb-3 font-semibold text-gray-900 process-category-title-dark"
					>
						{config.icon}
						{key.charAt(0).toUpperCase() +
							key.slice(1)}{key.includes("other") ? "s" : ""}
					</h3>
					<p class="process-page-description-dark">
						{config.description}
					</p>
				</div>
			{/each}
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
				placeholder="Search processes..."
				class="bg-white dark:bg-slate-700/60 pl-10 border-gray-200 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 focus:ring-orange-500 dark:focus:ring-emerald-500/50 text-gray-900 dark:placeholder:text-cyan-400/70 dark:text-cyan-200 placeholder:text-gray-500"
			/>
		</div>
	</div>

	<!-- Process Categories Grid -->
	{#if sortedCategories.length > 0}
		<div class="space-y-8" bind:this={toc.ref}>
			{#each sortedCategories as { key, data }}
				<ProcessCategoryCard categoryKey={key} category={data} />
			{/each}
		</div>

		<!-- Results Summary -->
		{#if searchQuery.trim()}
			<div class="mt-8 text-gray-600 dark:text-cyan-400/80 text-center">
				Showing {totalMatchingProcesses} matching processes across {sortedCategories.length}
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
				class="process-title-shadow mb-2 font-semibold text-gray-900 dark:text-cyan-100 text-xl"
			>
				No processes found
			</h3>
			<p
				class="process-description-shadow mb-4 text-muted-foreground dark:text-cyan-400/70"
			>
				Try searching with different keywords.
			</p>
			<Button onclick={() => (searchQuery = "")}>Clear Search</Button>
		</div>
	{/if}
</div>
