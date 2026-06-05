<script lang="ts">
	import { onMount } from "svelte";
	import { db, getAllLocalCustomBeans, type LocalCustomBean } from "$lib/db/localdb";
	import { dbUpdateTrigger, notifyUpdate } from "$lib/db/updates.svelte";
	import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
	import { Card } from "$lib/components/ui/card";
	import { Library, Plus } from "lucide-svelte";
	import { Button } from "$lib/components/ui/button";
	import { fade } from "svelte/transition";
	import AddBeanForm from "$lib/components/tasting/AddBeanForm.svelte";
	import * as Dialog from "$lib/components/ui/dialog";
	import { Input } from "$lib/components/ui/input/index.js";
	import { searchGenericBeans } from "$lib/utils/search";
	import { X, Search as SearchIcon } from "lucide-svelte";

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
</script>

<div class="space-y-8">
	<div class="flex sm:flex-row flex-col justify-between items-start sm:items-center gap-4">
		<h2 class="font-bold text-2xl tracking-tight">Your Private Collection</h2>
		<Button onclick={() => showAddDialog = true} class="justify-center gap-2 w-full sm:w-auto">
			<Plus size={18} /> Add Custom Bean
		</Button>
	</div>

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
		<div class="gap-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
			{#each Array(6) as _}
				<div class="bg-muted rounded-2xl h-80 animate-pulse"></div>
			{/each}
		</div>
	{:else if customBeans.length === 0}
		<Card class="flex flex-col items-center gap-6 p-12 border-dashed text-center">
			<div class="bg-muted p-6 rounded-full">
				<Library size={48} class="text-muted-foreground/30" />
			</div>
			<div class="space-y-2">
				<h2 class="font-bold text-xl">Your collection is empty</h2>
				<p class="max-w-sm text-muted-foreground">
					Start building your private database of coffees from local roasters or home roasts.
				</p>
			</div>
			<Button onclick={() => showAddDialog = true}>
				Add a Bean
			</Button>
		</Card>
	{:else}
		<div class="gap-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
			{#each filteredBeans as localBean (localBean.syncId)}
				<div transition:fade>
					<CoffeeBeanCard
						bean={{
							...localBean.beanData,
							savedBeanId: localBean.syncId
						}}
						vaultMode={true}
					/>
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
