<script lang="ts">
	import { onMount } from "svelte";
	import { db, getAllLocalCustomBeans, type LocalCustomBean } from "$lib/db/localdb";
	import { dbUpdateTrigger, notifyUpdate } from "$lib/db/updates.svelte";
	import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
	import { Card, CardContent } from "$lib/components/ui/card";
	import { Library, Plus, Clock, ArrowRight, Search as SearchIcon, X } from "lucide-svelte";
	import { Button } from "$lib/components/ui/button";
	import { fade } from "svelte/transition";
	import AddBeanForm from "$lib/components/tasting/AddBeanForm.svelte";
	import * as Dialog from "$lib/components/ui/dialog";
	import { Input } from "$lib/components/ui/input/index.js";
	import { searchGenericBeans } from "$lib/utils/search";

	let { data } = $props();

	let customBeans = $state<LocalCustomBean[]>(data.beans || []);
	let searchQuery = $state("");
	let isLoading = $state(customBeans.length === 0);
	let showAddDialog = $state(false);

	const filteredBeans = $derived.by(() => {
		if (!searchQuery.trim()) return customBeans;
		return searchGenericBeans(customBeans, searchQuery) as LocalCustomBean[];
	});

	// Reactive fetch based on database updates
	$effect(() => {
		// Accessing this property makes the effect depend on it
		const trigger = dbUpdateTrigger.customBeans;
		getAllLocalCustomBeans().then(beans => {
			customBeans = beans;
			isLoading = false;
			console.log(`[Collection] Loaded ${beans.length} custom beans`);
		});
	});

	async function refresh() {
		// No manual refresh needed with the reactive effect above,
		// but we keep the exported function name if other components use it
	}

	// Time-group labels for each bean to mirror the saved vault layout.
	let beansWithGroupLabels = $derived.by(() => {
		const result: (LocalCustomBean & {
			isFirstInGroup: boolean;
			groupPeriod: string;
		})[] = [];
		const now = new Date();
		const todayStart = new Date(
			now.getFullYear(),
			now.getMonth(),
			now.getDate(),
		);
		const yesterdayStart = new Date(todayStart);
		yesterdayStart.setDate(yesterdayStart.getDate() - 1);
		const weekStart = new Date(todayStart);
		weekStart.setDate(weekStart.getDate() - 7);
		const monthStart = new Date(todayStart);
		monthStart.setDate(monthStart.getDate() - 30);

		let lastPeriod = "";

		for (const bean of filteredBeans) {
			const updatedAt = new Date(bean.updatedAt || Date.now());
			let period = "";

			if (updatedAt >= todayStart) {
				period = "Today";
			} else if (updatedAt >= yesterdayStart) {
				period = "Yesterday";
			} else if (updatedAt >= weekStart) {
				period = "Past Week";
			} else if (updatedAt >= monthStart) {
				period = "Past Month";
			} else {
				period = updatedAt.toLocaleDateString("en-US", {
					month: "long",
					year: "numeric",
				});
			}

			const isFirstInGroup = period !== lastPeriod;
			result.push({
				...bean,
				isFirstInGroup,
				groupPeriod: period,
			});
			lastPeriod = period;
		}

		return result;
	});
</script>

<div class="space-y-8">
	<div class="flex sm:flex-row flex-col justify-between items-start sm:items-center gap-4">
		<h2 class="font-bold text-2xl tracking-tight">Your Private Collection</h2>
		<Button onclick={() => showAddDialog = true} class="justify-center gap-2 w-full sm:w-auto">
			<Plus size={18} /> Add Custom Bean
		</Button>
	</div>

	<p
		class="varietal-description-shadow mx-auto mb-8 max-w-3xl text-gray-600 dark:text-cyan-300/80 text-xl text-center"
	>
		{#if isLoading}
			Loading your collection...
		{:else if customBeans.length === 0}
			You haven't added any custom beans yet. Build your private database of
			local roasts and home experiments.
		{:else}
			You have <span class="font-bold">{customBeans.length}</span>
			custom {customBeans.length === 1 ? "bean" : "beans"} in your collection.
			Add tasting notes as you explore.
		{/if}
	</p>

	<!-- Search Bar -->
	<div class="mx-auto mb-12 w-full max-w-md">
		<div class="relative">
			<SearchIcon
				class="top-1/2 left-3 absolute w-4 h-4 text-gray-500 dark:text-cyan-400/70 -translate-y-1/2 transform"
			/>
			<Input
				type="text"
				placeholder="Search custom beans..."
				class="bg-white dark:bg-slate-700/60 pr-10 pl-10 border-gray-200 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 focus:ring-orange-500 dark:focus:ring-emerald-500/50 text-gray-900 dark:placeholder:text-cyan-400/70 dark:text-cyan-200 placeholder:text-gray-500"
				bind:value={searchQuery}
			/>
			{#if searchQuery}
				<button
					class="top-1/2 right-3 absolute p-1 text-muted-foreground hover:text-foreground -translate-y-1/2 transform"
					onclick={() => (searchQuery = "")}
					aria-label="Clear search"
				>
					<X class="w-4 h-4" />
				</button>
			{/if}
		</div>
	</div>

	{#if isLoading}
		<!-- Loading State (Skeleton) -->
		<div
			class="gap-x-4 gap-y-10 lg:gap-y-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
		>
			{#each Array(6) as _}
				<Card
					class="bg-white/50 dark:bg-slate-900/50 border-slate-200 dark:border-cyan-500/20 h-[500px] overflow-hidden animate-pulse"
				>
					<div class="bg-slate-200 dark:bg-slate-800 w-full h-48"></div>
					<CardContent class="p-6">
						<div
							class="bg-slate-200 dark:bg-slate-800 mb-4 rounded w-1/3 h-4"
						></div>
						<div
							class="bg-slate-200 dark:bg-slate-800 mb-2 rounded w-full h-8"
						></div>
						<div
							class="bg-slate-200 dark:bg-slate-800 mb-8 rounded w-2/3 h-4"
						></div>
						<div class="flex gap-2">
							<div
								class="bg-slate-200 dark:bg-slate-800 rounded-full w-16 h-6"
							></div>
							<div
								class="bg-slate-200 dark:bg-slate-800 rounded-full w-16 h-6"
							></div>
						</div>
					</CardContent>
				</Card>
			{/each}
		</div>
	{:else if customBeans.length === 0}
		<!-- Empty State -->
		<Card
			class="dark:bg-linear-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30"
		>
			<CardContent class="flex flex-col justify-center items-center py-16">
				<Library class="mb-4 w-16 h-16 text-muted-foreground" />
				<h2 class="mb-2 font-semibold text-xl">Your collection is empty</h2>
				<p class="mb-6 max-w-md text-muted-foreground text-center">
					Start building your private database of coffees from local roasters or home roasts.
				</p>
				<Button onclick={() => showAddDialog = true}>
					Add a Bean
				</Button>
			</CardContent>
		</Card>
	{:else if filteredBeans.length === 0 && searchQuery}
		<!-- No Search Results -->
		<Card
			class="dark:bg-slate-900/50 dark:border-cyan-500/20 border-dashed"
		>
			<CardContent class="flex flex-col justify-center items-center py-16">
				<SearchIcon class="opacity-50 mb-4 w-12 h-12 text-muted-foreground" />
				<h2 class="mb-2 font-semibold text-xl">No matching beans found</h2>
				<p class="max-w-md text-muted-foreground text-center">
					Try adjusting your search terms or clearing the search.
				</p>
				<Button variant="ghost" class="mt-4" onclick={() => (searchQuery = "")}>
					Clear Search
				</Button>
			</CardContent>
		</Card>
	{:else}
		<!-- Beans Grid Grouped by Time (Single Continuous Grid) -->
		<div
			class="gap-x-4 gap-y-10 lg:gap-y-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3"
		>
			{#each beansWithGroupLabels as localBean (localBean.syncId)}
				<div class="relative flex flex-col h-full">
					{#if localBean.isFirstInGroup}
						<div
							class="-top-6 left-0 absolute flex items-center gap-2 font-semibold text-gray-700 dark:text-cyan-300 text-sm whitespace-nowrap"
						>
							<Clock class="w-3.5 h-3.5" />
							{localBean.groupPeriod}
							<ArrowRight class="opacity-50 w-3.5 h-3.5" />
						</div>
					{/if}
					<div transition:fade|global class="h-full">
						<CoffeeBeanCard
							class="h-full"
							bean={{
								...localBean.beanData,
								savedBeanId: localBean.syncId
							}}
							vaultMode={true}
						/>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<Dialog.Root bind:open={showAddDialog}>
	<Dialog.Content class="sm:max-w-3xl max-h-[90vh] overflow-y-auto">
		<Dialog.Header>
			<Dialog.Title>Add Custom Bean</Dialog.Title>
			<Dialog.Description>
				Add a bean to your private collection. This will be available for tastings and synced across your devices.
			</Dialog.Description>
		</Dialog.Header>
		<AddBeanForm
			onSuccess={() => {
				showAddDialog = false;
				refresh();
			}}
			onCancel={() => showAddDialog = false}
		/>
	</Dialog.Content>
</Dialog.Root>

<svelte:head>
	<title>Private Collection | My Coffee Vault | Kissaten</title>
	<meta
		name="description"
		content="Your private collection of coffee beans"
	/>
	<meta name="robots" content="noindex,follow" />
	<link rel="canonical" href="https://kissaten.app/vault/collection" />
</svelte:head>
