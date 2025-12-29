<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Card, CardContent } from "$lib/components/ui/card/index.js";
	import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
	import { saveBean, unsaveBean } from "$lib/api/vault.remote";
	import { api } from "$lib/api";
	import { Coffee } from "lucide-svelte";
	import { toast } from "svelte-sonner";
	import { fade, slide } from "svelte/transition";

	let { data } = $props();

	// Use $state for reactive mutations
	let beans = $state(data.beans || []);
	let totalSaved = $derived(beans.length);

	async function performUnsave(savedBeanId: string) {
		const beanIndex = beans.findIndex((b) => b.savedBeanId === savedBeanId);
		let removedBean: any = null;
		let originalIndex = -1;

		if (beanIndex !== -1) {
			removedBean = beans[beanIndex];
			originalIndex = beanIndex;
			beans.splice(beanIndex, 1);
		}

		try {
			await unsaveBean({ savedBeanId });
			toast.success("Bean removed from vault", {
				action: {
					label: "Undo",
					onClick: async () => {
						try {
							if (removedBean) {
								await saveBean({
									beanUrlPath:
										removedBean.beanUrlPath ||
										api.getBeanUrlPath(removedBean),
									notes: removedBean.notes || "",
								});

								// Add back to the list at the same position (or push if index lost)
								if (originalIndex !== -1) {
									beans.splice(originalIndex, 0, removedBean);
								} else {
									beans.push(removedBean);
								}
								toast.success("Restored bean and notes");
							}
						} catch (e) {
							console.error("Failed to undo unsave:", e);
							toast.error("Failed to restore bean");
						}
					},
				},
			});
		} catch (error) {
			console.error("Failed to unsave bean:", error);
			toast.error("Failed to remove bean");
			// Rollback optimistic update immediately on error
			if (removedBean && originalIndex !== -1) {
				beans.splice(originalIndex, 0, removedBean);
			}
		}
	}

	async function handleUnsave(savedBeanId: string) {
		const bean = beans.find((b) => b.savedBeanId === savedBeanId);
		if (!bean) return;

		if (bean.notes && bean.notes.trim()) {
			toast(`Remove ${bean.name}?`, {
				description:
					"This bean has personal notes. Unsaving will remove them.",
				action: {
					label: "Confirm Unsave",
					onClick: () => performUnsave(savedBeanId),
				},
			});
		} else {
			await performUnsave(savedBeanId);
		}
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
		<h1
			class="varietal-title-shadow mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl"
		>
			My Coffee Vault
		</h1>
		<p
			class="varietal-description-shadow mx-auto mb-6 max-w-3xl text-gray-600 dark:text-cyan-300/80 text-xl"
		>
			{#if totalSaved === 0}
				You haven't saved any beans yet. Browse the catalog and save
				your favorites!
			{:else}
				Your personal collection of {totalSaved} saved coffee {totalSaved ===
				1
					? "bean"
					: "beans"}. Keep track of your favorites and add tasting
				notes as you explore.
			{/if}
		</p>
	</div>

	{#if beans.length === 0}
		<!-- Empty State -->
		<Card
			class="dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30"
		>
			<CardContent
				class="flex flex-col justify-center items-center py-16"
			>
				<Coffee class="mb-4 w-16 h-16 text-muted-foreground" />
				<h2 class="mb-2 font-semibold text-xl">Your vault is empty</h2>
				<p class="mb-6 max-w-md text-muted-foreground text-center">
					Start saving coffee beans you love to keep track of them and
					add your own tasting notes.
				</p>
				<Button href="/search">Browse Coffee Beans</Button>
			</CardContent>
		</Card>
	{:else}
		<!-- Beans Grid -->
		<div class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
			{#each beans as bean (bean.id)}
				<div transition:fade|global>
					<CoffeeBeanCard
						class="h-full"
						{bean}
						vaultMode={true}
						onRemove={handleUnsave}
						onNotesChange={(notes) => (bean.notes = notes)}
					/>
				</div>
			{/each}
		</div>
	{/if}
</div>
