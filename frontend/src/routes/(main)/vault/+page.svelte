<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import {
		Card,
		CardContent,
	} from "$lib/components/ui/card/index.js";
	import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
	import { unsaveBean, updateBeanNotes } from "$lib/api/vault.remote";
	import { Coffee } from "lucide-svelte";

	let { data } = $props();

	// Use $state for reactive mutations
	let beans = $state(data.beans || []);
	let totalSaved = $derived(beans.length);

	// Debounce timers for autosaving notes
	let debounceTimers = new Map<string, number>();

	async function handleUnsave(savedBeanId: string) {
		if (!confirm('Remove this bean from your vault?')) return;

		// Optimistic update - remove from UI immediately
		const beanIndex = beans.findIndex(b => b.savedBeanId === savedBeanId);
		if (beanIndex !== -1) {
			beans.splice(beanIndex, 1);
		}

		// Call the API to persist the change
		await unsaveBean({ savedBeanId });
	}

	function handleNotesChange(savedBeanId: string, notes: string) {
		// Optimistically update the notes in the local state
		const bean = beans.find(b => b.savedBeanId === savedBeanId);
		if (bean) {
			bean.notes = notes;
		}

		// Clear existing timer for this bean
		const existingTimer = debounceTimers.get(savedBeanId);
		if (existingTimer) {
			clearTimeout(existingTimer);
		}

		// Set new timer to save after 500ms of no typing
		const timer = setTimeout(() => {
			updateBeanNotes({ savedBeanId, notes });
			debounceTimers.delete(savedBeanId);
		}, 500);

		debounceTimers.set(savedBeanId, timer);
	}
</script>

<svelte:head>
	<title>My Coffee Vault - Kissaten</title>
	<meta
		name="description"
		content="Your saved coffee beans and tasting notes"
	/>
</svelte:head>

<div class="mx-auto px-4 py-8 max-w-7xl container">
	<!-- Header -->
	<div class="mb-12 text-center">
		<h1 class="varietal-title-shadow mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl">
			My Coffee Vault
		</h1>
		<p class="varietal-description-shadow mx-auto mb-6 max-w-3xl text-gray-600 dark:text-cyan-300/80 text-xl">
			{#if totalSaved === 0}
				You haven't saved any beans yet. Browse the catalog and save your favorites!
			{:else}
				Your personal collection of {totalSaved} saved coffee {totalSaved === 1 ? 'bean' : 'beans'}. Keep track of your favorites and add tasting notes as you explore.
			{/if}
		</p>
	</div>

	{#if beans.length === 0}
		<!-- Empty State -->
		<Card class="dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30">
			<CardContent class="flex flex-col justify-center items-center py-16">
				<Coffee class="mb-4 w-16 h-16 text-muted-foreground" />
				<h2 class="mb-2 font-semibold text-xl">Your vault is empty</h2>
				<p class="mb-6 max-w-md text-muted-foreground text-center">
					Start saving coffee beans you love to keep track of them and add your own tasting notes.
				</p>
				<Button href="/search">Browse Coffee Beans</Button>
			</CardContent>
		</Card>
	{:else}
		<!-- Beans Grid -->
		<div class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
			{#each beans as bean (bean.id)}
					<CoffeeBeanCard
						{bean}
						showVaultFeatures={true}
						onRemove={handleUnsave}
						onNotesChange={handleNotesChange}
					/>
			{/each}
		</div>
	{/if}
</div>
