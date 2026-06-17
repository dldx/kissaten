<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Card, CardContent } from "$lib/components/ui/card/index.js";
	import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
	import { unsaveBean } from "$lib/api/vault.remote";
	import { deleteCustomBean } from "$lib/api/custom_beans.remote";
	import { api, type CoffeeBean } from "$lib/api";
	import { Clock, ArrowRight, Search as SearchIcon, X } from "lucide-svelte";
	import { toast } from "svelte-sonner";
	import { fade } from "svelte/transition";
	import { onMount, untrack } from "svelte";
	import { db, getRecentlyViewedBeans } from "$lib/db/localdb";
	import { notifyUpdate, dbUpdateTrigger } from "$lib/db/updates.svelte";
	import { getSavedBeans } from "$lib/api/vault.remote";
	import { Input } from "$lib/components/ui/input/index.js";
	import { searchGenericBeans } from "$lib/utils/search";

	interface RecentBean extends CoffeeBean {
		savedAt?: string;
		savedBeanId?: string;
		notes?: string;
	}

	let { data } = $props();

	let searchQuery = $state("");
	let isLoadingRecent = $state(false);
	let allRecentlyViewed = $state<any[]>(data.initialRecentlyViewed || []);
	let savedBeans = $state<any[]>(data.initialSavedBeans || []);
	let currentRecentPage = $state(1);

	// Pagination for recently viewed
	const RECENT_PAGE_SIZE = 9; // 3x3 grid

	// The active list being displayed
	const displayedBeans = $derived.by(() => {
		const query = searchQuery.trim();
		const allSaved = savedBeans;

		if (query) {
			// Search mode: show all matches across full history
			const scored = searchGenericBeans(allRecentlyViewed, query);
			return scored
				.filter(v => v.beanData)
				.map(v => {
					const saved = allSaved.find(s => s.beanUrlPath === v.beanUrlPath);
					return {
						...v.beanData!,
						savedBeanId: saved?.id,
						notes: saved?.notes,
						savedAt: new Date((v as any).viewedAt || Date.now()).toISOString()
					} as RecentBean;
				});
		} else {
			// Normal mode: show paged results
			const startIdx = 0;
			const endIdx = currentRecentPage * RECENT_PAGE_SIZE;
			return allRecentlyViewed.slice(startIdx, endIdx).map((item) => {
				const saved = allSaved.find(s => s.beanUrlPath === item.beanUrlPath);
				return {
					...item.beanData,
					savedBeanId: saved?.id,
					notes: saved?.notes,
					savedAt: new Date(item.viewedAt).toISOString(),
				} as RecentBean;
			});
		}
	});

	// Pagination derived values
	let totalRecentPages = $derived(
		Math.ceil(allRecentlyViewed.length / RECENT_PAGE_SIZE),
	);
	let hasMoreRecent = $derived(!searchQuery && currentRecentPage < totalRecentPages);

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

		for (const bean of displayedBeans) {
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
		if (allRecentlyViewed.length === 0) {
			await loadRecentBeans();
		}
	});

	// Reactive fetch based on database updates
	$effect(() => {
		const _s = dbUpdateTrigger.savedBeans;
		const _c = dbUpdateTrigger.customBeans;

		untrack(() => {
			loadRecentBeans();
		});
	});

	async function loadRecentBeans() {
		isLoadingRecent = true;
		try {
			const [recent, saved] = await Promise.all([
				getRecentlyViewedBeans(),
				getSavedBeans()
			]);
			allRecentlyViewed = recent;
			savedBeans = saved;
		} catch (error) {
			console.error("Error loading recent beans:", error);
			toast.error("Failed to load recently viewed beans");
		} finally {
			isLoadingRecent = false;
		}
	}

	function loadNextRecentPage() {
		if (currentRecentPage < totalRecentPages) {
			currentRecentPage++;
		}
	}

	function loadPrevRecentPage() {
		if (currentRecentPage > 1) {
			currentRecentPage--;
		}
	}
</script>

<svelte:head>
	<title>Recently Viewed | My Coffee Vault | Kissaten</title>
	<meta name="description" content="Your recently viewed coffee beans" />
	<meta name="robots" content="noindex,follow" />
	<link rel="canonical" href="https://kissaten.app/vault/recently-viewed" />
</svelte:head>

<p
	class="varietal-description-shadow mx-auto mb-8 max-w-3xl text-gray-600 dark:text-cyan-300/80 text-xl text-center"
>
	View your recently viewed coffee beans. This data is stored locally on your
	device.
</p>

<!-- Search Bar -->
<div class="mx-auto mb-12 w-full max-w-md">
	<div class="relative">
		<SearchIcon
			class="top-1/2 left-3 absolute w-4 h-4 text-gray-500 dark:text-cyan-400/70 -translate-y-1/2 transform"
		/>
		<Input
			type="text"
			placeholder="Search recently viewed beans..."
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

{#if isLoadingRecent}
	<div class="flex justify-center items-center py-16">
		<p class="text-muted-foreground">Loading...</p>
	</div>
{:else if displayedBeans.length === 0}
	<Card
		class="dark:bg-linear-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30"
	>
		<CardContent class="flex flex-col justify-center items-center py-16">
			{#if searchQuery}
				<SearchIcon class="mb-4 w-16 h-16 text-muted-foreground" />
				<h2 class="mb-2 font-semibold text-xl">No matches found</h2>
				<p class="mb-6 max-w-md text-muted-foreground text-center">
					We couldn't find any recently viewed beans matching "{searchQuery}".
				</p>
				<Button variant="outline" onclick={() => (searchQuery = "")}>Clear Search</Button>
			{:else}
				<Clock class="mb-4 w-16 h-16 text-muted-foreground" />
				<h2 class="mb-2 font-semibold text-xl">No recent views</h2>
				<p class="mb-6 max-w-md text-muted-foreground text-center">
					Your recently viewed beans will appear here as you browse.
				</p>
				<Button href="/search">Browse Coffee Beans</Button>
			{/if}
		</CardContent>
	</Card>
{:else}
	<!-- Recently Viewed Beans Grid (Single Continuous Grid) -->
	<div
		class="gap-x-4 gap-y-10 lg:gap-y-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
	>
		{#each beansWithGroupLabels as bean (bean.id + "-" + (bean.savedBeanId || "unsaved"))}
			<div class="relative flex flex-col h-full">
				{#if bean.isFirstInGroup}
					<div
						class="-top-6 left-0 absolute flex items-center gap-2 font-semibold text-gray-700 dark:text-cyan-300 text-sm whitespace-nowrap"
					>
						<Clock class="w-3.5 h-3.5" />
						{bean.groupPeriod}
						<ArrowRight class="opacity-50 w-3.5 h-3.5" />
					</div>
				{/if}
				<div transition:fade|global class="h-full">
					{#if bean.savedBeanId}
						<!-- Saved beans: show in vault mode with internal links -->
						<CoffeeBeanCard
							class="h-full"
							{bean}
							vaultMode={true}
							onNotesChange={(notes) => (bean.notes = notes)}
						/>
					{:else}
						<!-- Unsaved beans: wrap in link to make entire card clickable -->
						<CoffeeBeanCard
							class="h-full"
							{bean}
							vaultMode={false}
						/>
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
