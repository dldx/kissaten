<script lang="ts">
	import { onMount } from "svelte";
	import { getAllLocalCustomBeans, type LocalCustomBean } from "$lib/db/localdb";
	import { dbUpdateTrigger } from "$lib/db/updates.svelte";
	import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
	import { Card } from "$lib/components/ui/card";
	import { Library, Plus } from "lucide-svelte";
	import { Button } from "$lib/components/ui/button";
	import { fade } from "svelte/transition";
	import AddBeanForm from "$lib/components/tasting/AddBeanForm.svelte";
	import * as Dialog from "$lib/components/ui/dialog";

	let customBeans = $state<LocalCustomBean[]>([]);
	let isLoading = $state(true);
	let showAddDialog = $state(false);

	// Reactive fetch based on database updates
	$effect(() => {
		// Accessing this property makes the effect depend on it
		const trigger = dbUpdateTrigger.customBeans;
		getAllLocalCustomBeans().then(beans => {
			customBeans = beans;
			isLoading = false;
		});
	});

	async function refresh() {
		// No manual refresh needed with the reactive effect above,
		// but we keep the exported function name if other components use it
	}
</script>

<div class="space-y-8">
	<div class="flex justify-between items-center">
		<h2 class="font-bold text-2xl tracking-tight">Your Private Collection</h2>
		<Button onclick={() => showAddDialog = true} class="gap-2">
			<Plus size={18} /> Add Custom Bean
		</Button>
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
				Create Your First Bean
			</Button>
		</Card>
	{:else}
		<div class="gap-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
			{#each customBeans as localBean (localBean.syncId)}
				<div transition:fade>
					<CoffeeBeanCard
						bean={localBean.beanData}
						showSaveButton={false}
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
