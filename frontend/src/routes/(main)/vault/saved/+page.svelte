<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Card, CardContent } from "$lib/components/ui/card/index.js";
	import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
	import { saveBean, unsaveBean } from "$lib/api/vault.remote";
	import { api, type CoffeeBean } from "$lib/api";
	import { Coffee, Clock, ArrowRight } from "lucide-svelte";
	import { toast } from "svelte-sonner";
	import { fade } from "svelte/transition";

	interface SavedBean extends CoffeeBean {
		savedAt?: string;
		savedBeanId?: string;
		notes?: string;
	}

	let { data } = $props();

	// Initialize state from data for SSR support
	let beans = $state<SavedBean[]>(data.beans || []);

	// Sync with data whenever it changes (pagination/navigation)
	$effect(() => {
		beans = [...(data.beans || [])];

		// Scroll to top when page changes
		if (data.pagination?.page && typeof window !== "undefined") {
			window.scrollTo({ top: 0, behavior: "smooth" });
		}
	});

	let uniqueCountries = $derived.by(() => {
		const countries = beans
			.map((bean) => bean.country_full_name)
			.filter((country) => country != null);
		return [...new Set(countries)];
	});
	let uniqueRoasters = $derived.by(() => {
		const roasters = beans
			.map((bean) => bean.roaster)
			.filter((roaster) => roaster != null);
		return [...new Set(roasters)];
	});

	let totalSaved = $derived(data.totalSaved || 0);
	let pagination = $derived(data.pagination);

	// Flat list of beans with group info to avoid grid gaps
	let beansWithGroupLabels = $derived.by(() => {
		const result: (SavedBean & {
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

		for (const bean of beans) {
			const savedAt = new Date(bean.savedAt || new Date());
			let period = "";

			if (savedAt >= todayStart) {
				period = "Today";
			} else if (savedAt >= yesterdayStart) {
				period = "Yesterday";
			} else if (savedAt >= weekStart) {
				period = "Past Week";
			} else if (savedAt >= monthStart) {
				period = "Past Month";
			} else {
				period = savedAt.toLocaleDateString("en-US", {
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
	<title>Saved Beans - My Coffee Vault - Kissaten</title>
	<meta
		name="description"
		content="Your saved coffee beans and tasting notes"
	/>
</svelte:head>

<p
	class="varietal-description-shadow mx-auto mb-6 max-w-3xl text-gray-600 dark:text-cyan-300/80 text-xl text-center"
>
	{#if totalSaved === 0}
		You haven't saved any beans yet. Browse the catalog and save your
		favorites!
	{:else}
		You have saved <span class="font-bold"
			>{totalSaved}
			coffee {totalSaved === 1 ? "bean" : "beans"}</span
		>
		from
		<span class="font-bold"
			>{uniqueCountries.length}
			countries</span
		>
		(<span class="font-bold">{uniqueRoasters.length} roasters</span>). Keep
		track of your favorites and add tasting notes as you explore.
	{/if}
</p>

{#if beans.length === 0 && totalSaved === 0}
	<!-- Empty State -->
	<Card
		class="dark:bg-linear-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30"
	>
		<CardContent class="flex flex-col justify-center items-center py-16">
			<Coffee class="mb-4 w-16 h-16 text-muted-foreground" />
			<h2 class="mb-2 font-semibold text-xl">Your vault is empty</h2>
			<p class="mb-6 max-w-md text-muted-foreground text-center">
				Start saving coffee beans you love to keep track of them and add
				your own tasting notes.
			</p>
			<Button href="/search">Browse Coffee Beans</Button>
		</CardContent>
	</Card>
{:else}
	<!-- Beans Grid Grouped by Time (Single Continuous Grid) -->
	<div
		class="gap-x-4 gap-y-10 lg:gap-y-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 items-stretch"
	>
		{#each beansWithGroupLabels as bean (bean.id)}
			<div
				class="relative flex flex-col h-full {bean.isFirstInGroup
					? 'pt-8'
					: ''}"
			>
				{#if bean.isFirstInGroup}
					<div
						class="top-0 left-0 absolute flex items-center gap-2 mb-2 font-semibold text-gray-700 dark:text-cyan-300 text-sm whitespace-nowrap"
					>
						<Clock class="w-3.5 h-3.5" />
						{bean.groupPeriod}
						<ArrowRight class="w-3.5 h-3.5 opacity-50" />
					</div>
				{/if}
				<div transition:fade|global class="h-full">
					<CoffeeBeanCard
						class="h-full"
						{bean}
						vaultMode={true}
						onRemove={handleUnsave}
						onNotesChange={(notes) => (bean.notes = notes)}
					/>
				</div>
			</div>
		{/each}
	</div>

	<!-- Pagination Controls -->
	{#if pagination && pagination.total_pages > 1}
		<div class="flex justify-center items-center gap-4 mt-8">
			<Button
				variant="outline"
				href="?page={pagination.page - 1}"
				disabled={!pagination.has_previous}
			>
				Previous
			</Button>

			<span class="text-muted-foreground text-sm">
				Page {pagination.page} of {pagination.total_pages}
			</span>

			<Button
				variant="outline"
				href="?page={pagination.page + 1}"
				disabled={!pagination.has_next}
			>
				Next
			</Button>
		</div>
	{/if}
{/if}
