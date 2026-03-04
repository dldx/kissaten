<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Card, CardContent } from "$lib/components/ui/card/index.js";
	import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
	import { unsaveBean } from "$lib/api/vault.remote";
	import { api, type CoffeeBean } from "$lib/api";
	import { Clock, ArrowRight } from "lucide-svelte";
	import { toast } from "svelte-sonner";
	import { fade } from "svelte/transition";
	import { onMount } from "svelte";
	import { getRecentlyViewedBeans } from "$lib/db/localdb";
	import { getSavedBeans } from "$lib/api/vault.remote";

	interface RecentBean extends CoffeeBean {
		savedAt?: string;
		savedBeanId?: string;
		notes?: string;
	}

	let { data } = $props();

	let recentBeans = $state<RecentBean[]>([]);
	let isLoadingRecent = $state(false);
	let allRecentlyViewed = $state<any[]>([]);

	// Pagination for recently viewed
	const RECENT_PAGE_SIZE = 9; // 3x3 grid
	let currentRecentPage = $state(1);
	let totalRecentPages = $derived(
		Math.ceil(allRecentlyViewed.length / RECENT_PAGE_SIZE),
	);
	let hasMoreRecent = $derived(currentRecentPage < totalRecentPages);

	// Group beans by time period
	// Flat list with group labels for continuous grid
	let beansWithGroupLabels = $derived.by(() => {
		const result: (RecentBean & {
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

		for (const bean of recentBeans) {
			const viewedAt = new Date(bean.savedAt || new Date());
			let period = "";

			if (viewedAt >= todayStart) {
				period = "Today";
			} else if (viewedAt >= yesterdayStart) {
				period = "Yesterday";
			} else if (viewedAt >= weekStart) {
				period = "Past Week";
			} else if (viewedAt >= monthStart) {
				period = "Past Month";
			} else {
				period = viewedAt.toLocaleDateString("en-US", {
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

	// Load recently viewed beans on mount
	onMount(async () => {
		await loadRecentBeans();
	});

	async function loadRecentBeans(page: number = 1) {
		isLoadingRecent = true;
		try {
			// First time loading - get all recently viewed from IndexedDB
			if (allRecentlyViewed.length === 0) {
				allRecentlyViewed = await getRecentlyViewedBeans();
			}

			if (allRecentlyViewed.length > 0) {
				// Calculate which beans to display for this page
				const startIndex = (page - 1) * RECENT_PAGE_SIZE;
				const endIndex = startIndex + RECENT_PAGE_SIZE;
				const pageItems = allRecentlyViewed.slice(startIndex, endIndex);

				// Get saved beans to merge with recently viewed
				const savedBeans = await getSavedBeans();

				// Use cached bean data from IndexedDB, merge with saved status and viewedAt
				const beansWithSavedStatus = pageItems.map((item) => {
					const savedBean = savedBeans.find(
						(sb) => sb.beanUrlPath === item.beanUrlPath,
					);
					return {
						...item.beanData,
						savedBeanId: savedBean?.id,
						notes: savedBean?.notes,
						savedAt: item.viewedAt, // Use viewedAt from IndexedDB for time grouping
						_originalSavedAt: savedBean?.createdAt,
					};
				});

				recentBeans = beansWithSavedStatus;
				currentRecentPage = page;

				// Scroll to top of the list when page changes
				if (typeof window !== "undefined" && page > 1) {
					window.scrollTo({ top: 0, behavior: "smooth" });
				}
			}
		} catch (error) {
			console.error("Error loading recent beans:", error);
			toast.error("Failed to load recently viewed beans");
		} finally {
			isLoadingRecent = false;
		}
	}

	async function loadNextRecentPage() {
		if (hasMoreRecent) {
			await loadRecentBeans(currentRecentPage + 1);
		}
	}

	async function loadPrevRecentPage() {
		if (currentRecentPage > 1) {
			await loadRecentBeans(currentRecentPage - 1);
		}
	}

	async function handleBeanSaved() {
		// Refresh the recently viewed beans to update saved status
		console.log(
			"[Recently Viewed] Handling bean saved, refreshing recent beans",
		);
		// Small delay to ensure the save operation is fully complete on the server
		await new Promise((resolve) => setTimeout(resolve, 150));

		// Fetch updated saved beans list
		const savedBeans = await getSavedBeans();
		console.log(
			"[Recently Viewed] Fetched saved beans:",
			savedBeans.length,
		);

		// Create a completely new array to force reactivity
		const updatedBeans = [];
		for (const bean of recentBeans) {
			const savedBean = savedBeans.find(
				(sb) => sb.beanUrlPath === bean.bean_url_path,
			);
			if (savedBean) {
				console.log(
					"[Recently Viewed] Bean is now saved:",
					bean.name,
					"savedBeanId:",
					savedBean.id,
				);
				// Bean is saved - create new object with saved metadata
				updatedBeans.push({
					...bean,
					savedBeanId: savedBean.id,
					notes: savedBean.notes,
					savedAt: savedBean.createdAt,
				});
			} else {
				// Bean is not saved
				updatedBeans.push(bean);
			}
		}

		// Assign completely new array reference
		recentBeans = updatedBeans;
		console.log(
			"[Recently Viewed] Recent beans updated, total:",
			recentBeans.length,
		);
	}

	async function handleUnsave(savedBeanId: string) {
		const bean = recentBeans.find((b) => b.savedBeanId === savedBeanId);
		if (!bean) return;

		const performUnsaveAndRefresh = async () => {
			try {
				await unsaveBean({ savedBeanId });
				toast.success("Bean removed from vault");

				// Create completely new array to force reactivity
				const updatedBeans = recentBeans.map((b) => {
					if (b.savedBeanId === savedBeanId) {
						// Create new object without saved properties
						const {
							savedBeanId: _,
							notes: __,
							savedAt: ___,
							...rest
						} = b;
						return {
							...rest,
							savedBeanId: undefined,
							notes: undefined,
							savedAt: undefined,
						};
					}
					return b;
				});
				recentBeans = updatedBeans;
			} catch (error) {
				console.error("Failed to unsave bean:", error);
				toast.error("Failed to remove bean");
			}
		};

		if (bean.notes && bean.notes.trim()) {
			toast(`Remove ${bean.name}?`, {
				description:
					"This bean has personal notes. Unsaving will remove them.",
				action: {
					label: "Confirm Unsave",
					onClick: performUnsaveAndRefresh,
				},
			});
		} else {
			await performUnsaveAndRefresh();
		}
	}
</script>

<svelte:head>
	<title>Recently Viewed - My Coffee Vault - Kissaten</title>
	<meta name="description" content="Your recently viewed coffee beans" />
</svelte:head>

<p
	class="varietal-description-shadow mx-auto mb-6 max-w-3xl text-gray-600 dark:text-cyan-300/80 text-xl text-center"
>
	View your recently viewed coffee beans. This data is stored locally on your
	device.
</p>

{#if isLoadingRecent}
	<div class="flex justify-center items-center py-16">
		<p class="text-muted-foreground">Loading...</p>
	</div>
{:else if recentBeans.length === 0 && allRecentlyViewed.length === 0}
	<Card
		class="dark:bg-linear-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30"
	>
		<CardContent class="flex flex-col justify-center items-center py-16">
			<Clock class="mb-4 w-16 h-16 text-muted-foreground" />
			<h2 class="mb-2 font-semibold text-xl">No recent views</h2>
			<p class="mb-6 max-w-md text-muted-foreground text-center">
				Your recently viewed beans will appear here as you browse.
			</p>
			<Button href="/search">Browse Coffee Beans</Button>
		</CardContent>
	</Card>
{:else}
	<!-- Recently Viewed Beans Grid (Single Continuous Grid) -->
	<div class="gap-x-4 gap-y-10 grid grid-cols-2 lg:grid-cols-3 items-stretch">
		{#each beansWithGroupLabels as bean (bean.id + "-" + (bean.savedBeanId || "unsaved"))}
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
					{#if bean.savedBeanId}
						<!-- Saved beans: show in vault mode with internal links -->
						<CoffeeBeanCard
							class="h-full"
							{bean}
							vaultMode={true}
							onRemove={handleUnsave}
							onNotesChange={(notes) => (bean.notes = notes)}
							onSave={handleBeanSaved}
						/>
					{:else}
						<!-- Unsaved beans: wrap in link to make entire card clickable -->
						<a
							href={"/roasters" + bean.bean_url_path}
							class="block h-full"
						>
							<CoffeeBeanCard
								class="h-full"
								{bean}
								vaultMode={false}
								onSave={handleBeanSaved}
							/>
						</a>
					{/if}
				</div>
			</div>
		{/each}
	</div>

	<!-- Pagination Controls -->
	{#if totalRecentPages > 1}
		<div class="flex justify-center items-center gap-4 mt-8">
			<Button
				variant="outline"
				onclick={loadPrevRecentPage}
				disabled={currentRecentPage === 1 || isLoadingRecent}
			>
				Previous
			</Button>
			<span class="text-muted-foreground text-sm">
				Page {currentRecentPage} of {totalRecentPages}
			</span>
			<Button
				variant="outline"
				onclick={loadNextRecentPage}
				disabled={!hasMoreRecent || isLoadingRecent}
			>
				Next
			</Button>
		</div>
	{/if}
{/if}
