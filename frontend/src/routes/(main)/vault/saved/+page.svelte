<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Card, CardContent } from "$lib/components/ui/card/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
	import { saveBean, unsaveBean } from "$lib/api/vault.remote";
	import { deleteCustomBean } from "$lib/api/custom_beans.remote";
	import { api, type CoffeeBean } from "$lib/api";
	import { db, type LocalSavedBean, type LocalCustomBean } from "$lib/db/localdb";
	import { dbUpdateTrigger, notifyUpdate } from "$lib/db/updates.svelte";
	import { searchGenericBeans } from "$lib/utils/search";
	import { Coffee, Clock, ArrowRight, Search as SearchIcon, X, History, Library } from "lucide-svelte";
	import { toast } from "svelte-sonner";
	import { fade } from "svelte/transition";
	import { untrack, onMount } from "svelte";

	interface SavedBean extends CoffeeBean {
		savedAt?: string;
		savedBeanId?: string;
		notes?: string;
		isCustom?: boolean;
	}

	let { data } = $props();

	let searchQuery = $state("");

	let isLoading = $state(data.beans.length === 0);

	let beans = $state<SavedBean[]>(data.beans || []);
	let recentlyViewed = $state<CoffeeBean[]>([]);
	let totalSaved = $state(data.totalSaved || 0);

	// Reactive fetch based on database updates
	$effect(() => {
		// Explicitly depend on search query and all relevant triggers
		const query = searchQuery;
		const _sTrigger = dbUpdateTrigger.savedBeans;
		const _cTrigger = dbUpdateTrigger.customBeans;
		const userId = data.userId;
		let active = true;

		const fetchData = async () => {
			// Map saved beans
			const [saved, custom, globalViewed] = await Promise.all([
				db.savedBeans
					.filter(b => !b.deletedAt && (b.ownerId === userId || !b.ownerId || !userId))
					.toArray(),
				db.customBeans
					.filter(b => !b.deletedAt && (b.ownerId === userId || !b.ownerId || !userId))
					.toArray(),
				db.recentlyViewed.toArray()
			]);

			if (!active) return;

			// Total count for derived stats
			const totalCount = saved.length + custom.length;

			// 1. Process Saved + Custom Beans (Main Results)
			const allSavedRecords = [
				...saved,
				...custom.map(c => ({
					...c,
					notes: "", // Custom beans don't have separate notes yet
					createdAt: c.updatedAt, // Use updatedAt as placeholder
					isCustom: true
				}))
			] as (LocalSavedBean | LocalCustomBean)[];

			let result: SavedBean[] = [];
			const cleanQuery = query.trim();

			if (cleanQuery) {
				const scored = searchGenericBeans(allSavedRecords, cleanQuery) as (LocalSavedBean | LocalCustomBean)[];
				result = scored
					.filter(b => b.beanData)
					.map(b => ({
						...b.beanData!,
						savedBeanId: b.syncId,
						notes: (b as any).notes || "",
						savedAt: new Date((b as any).createdAt || (b as any).updatedAt).toISOString(),
						updatedAt: new Date((b as any).updatedAt).toISOString(),
						isCustom: (b as any).isCustom || false
					}));
			} else {
				// No query - show saved beans sorted by date
				result = allSavedRecords
					.filter(b => b.beanData)
					.map(b => ({
						...b.beanData!,
						savedBeanId: b.syncId,
						notes: (b as any).notes || "",
						savedAt: new Date((b as any).createdAt || (b as any).updatedAt).toISOString(),
						updatedAt: new Date((b as any).updatedAt).toISOString(),
						isCustom: (b as any).isCustom || false
					}))
					.sort((a, b) => new Date(b.savedAt!).getTime() - new Date(a.savedAt!).getTime());
			}

			// 2. Process Recently Viewed (Separate section in search)
			let searchedViewed: CoffeeBean[] = [];
			if (cleanQuery) {
				const scoredViewed = searchGenericBeans(globalViewed, cleanQuery);
				searchedViewed = scoredViewed
					.filter(v => v.beanData)
					.map(v => v.beanData!);
			}

			if (!active) return;

			// Batch state update
			untrack(() => {
				if (!active) return;
				beans = result;
				totalSaved = totalCount;
				recentlyViewed = searchedViewed;
				isLoading = false;
			});
		};

		fetchData();
		return () => { active = false; };
	});

	let uniqueCountries = $derived.by(() => {
		const countries = beans
			.map((bean) => api.getPrimaryOrigin(bean)?.country_full_name)
			.filter((country) => country != null);
		return [...new Set(countries)];
	});
	let uniqueRoasters = $derived.by(() => {
		const roasters = beans
			.map((bean) => bean.roaster)
			.filter((roaster) => roaster != null);
		return [...new Set(roasters)];
	});

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
</script>

<svelte:head>
	<title>Saved Beans - My Coffee Vault - Kissaten</title>
	<meta
		name="description"
		content="Your saved coffee beans and tasting notes"
	/>
</svelte:head>

<p
	class="varietal-description-shadow mx-auto mb-8 max-w-3xl text-gray-600 dark:text-cyan-300/80 text-xl text-center"
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

<!-- Search and Filter Bar -->
<div class="mx-auto mb-12 max-w-md">
	<div class="relative">
		<SearchIcon
			class="top-1/2 left-3 absolute w-4 h-4 text-gray-500 dark:text-cyan-400/70 -translate-y-1/2 transform"
		/>
		<Input
			type="text"
			placeholder="Search by name, roaster, origin..."
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
{:else if beans.length === 0 && totalSaved === 0}
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
{:else if beans.length === 0 && searchQuery}
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
		{#each beansWithGroupLabels as bean (bean.savedBeanId)}
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
					<CoffeeBeanCard
						class="h-full"
						{bean}
						vaultMode={true}
						onNotesChange={(notes) => (bean.notes = notes)}
					/>
				</div>
			</div>
		{/each}
	</div>

	<!-- Removed Pagination Controls - Search is now continuous local -->

	{#if searchQuery && recentlyViewed.length > 0}
		<div class="mt-20 pt-12 border-slate-200 dark:border-cyan-500/20 border-t">
			<div class="flex items-center gap-3 mb-8">
				<div class="bg-cyan-100 dark:bg-cyan-900/40 p-2 rounded-lg text-cyan-600 dark:text-cyan-400">
					<History class="w-5 h-5" />
				</div>
				<h3 class="font-bold text-xl tracking-tight">Matching Recently Viewed</h3>
			</div>

			<div class="gap-x-4 gap-y-10 lg:gap-y-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
				{#each recentlyViewed as bean (bean.name + (bean.bean_url_path || ""))}
					<div transition:fade|global>
						<CoffeeBeanCard {bean} />
					</div>
				{/each}
			</div>
		</div>
	{/if}
{/if}
