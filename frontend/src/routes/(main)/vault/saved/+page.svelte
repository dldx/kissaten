<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Card, CardContent } from "$lib/components/ui/card/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
	import { api, type CoffeeBean } from "$lib/api";
	import {
		db,
		type LocalSavedBean,
		type LocalCustomBean,
		type RecentlyViewedBean
	} from "$lib/db/localdb";
	import { dbUpdateTrigger } from "$lib/db/updates.svelte";
	import { searchGenericBeans } from "$lib/utils/search";
	import { Coffee, Clock, ArrowRight, Search as SearchIcon, X, History } from "lucide-svelte";
	import { untrack } from "svelte";

	interface SavedBean extends CoffeeBean {
		savedAt?: string;
		updatedAt?: string;
		savedBeanId?: string;
		notes?: string;
		isCustom?: boolean;
	}

	let { data } = $props();

	let searchQuery = $state("");
	let debouncedSearchQuery = $state("");
	let debounceTimer: ReturnType<typeof setTimeout>;

	$effect(() => {
		const value = searchQuery;
		if (debounceTimer) clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => {
			debouncedSearchQuery = value;
		}, 200);

		return () => {
			if (debounceTimer) clearTimeout(debounceTimer);
		};
	});

	let isLoading = $state(!(data.savedRecords ?? []).some((b) => b.beanData));

	function mergeRecords(
		saved: LocalSavedBean[],
		custom: LocalCustomBean[]
	): (LocalSavedBean | LocalCustomBean)[] {
		return [
			...saved,
			...custom.map(c => ({
				...c,
				notes: "", // Custom beans don't have separate notes yet
				createdAt: c.updatedAt, // Use updatedAt as placeholder
				isCustom: true
			}))
		] as (LocalSavedBean | LocalCustomBean)[];
	}

	let allSavedRecords = $state<(LocalSavedBean | LocalCustomBean)[]>(
		mergeRecords(data.savedRecords ?? [], data.customRecords ?? [])
	);
	let allViewed = $state<RecentlyViewedBean[]>([]);
	let totalSaved = $state(data.totalSaved ?? 0);

	// Stable mapping so existing cards keep the same `bean` object across
	// searches: keyed on the Dexie record object identity.
	const mappedBeans = new WeakMap<object, SavedBean>();
	function toSavedBean(b: LocalSavedBean | LocalCustomBean): SavedBean {
		const cached = mappedBeans.get(b);
		if (cached) return cached;
		const mapped: SavedBean = {
			...b.beanData!,
			savedBeanId: b.syncId,
			notes: (b as any).notes || "",
			savedAt: new Date((b as any).createdAt || (b as any).updatedAt).toISOString(),
			updatedAt: new Date((b as any).updatedAt).toISOString(),
			isCustom: (b as any).isCustom || false
		};
		mappedBeans.set(b, mapped);
		return mapped;
	}

	// Dexie reads happen only when the DB actually changes (save/unsave/sync),
	// never per keystroke. Filtering/searching is done in memory via $derived.
	$effect(() => {
		// Explicitly depend on all relevant triggers
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

			// Saved-bean beanData is rehydrated upstream by the saved-bean sync
			// (savedBeanSync.ts), which runs on page load and notifies on change
			// so this effect re-renders once data is populated.

			// Total count for derived stats
			const totalCount = saved.length + custom.length;

			// Batch state update
			untrack(() => {
				if (!active) return;
				allSavedRecords = mergeRecords(saved, custom);
				allViewed = globalViewed;
				totalSaved = totalCount;
				isLoading = false;
			});
		};

		fetchData();
		return () => { active = false; };
	});

	let beans = $derived.by(() => {
		const query = debouncedSearchQuery.trim();
		if (query) {
			const scored = searchGenericBeans(allSavedRecords, query) as (LocalSavedBean | LocalCustomBean)[];
			return scored
				.filter(b => b.beanData)
				.map(toSavedBean);
		}
		// No query - show saved beans sorted by date
		return allSavedRecords
			.filter(b => b.beanData)
			.map(toSavedBean)
			.sort((a, b) => new Date(b.savedAt!).getTime() - new Date(a.savedAt!).getTime());
	});

	let recentlyViewed = $derived.by(() => {
		const query = debouncedSearchQuery.trim();
		if (!query) return [] as CoffeeBean[];
		const scoredViewed = searchGenericBeans(allViewed, query);
		const searchedViewed = scoredViewed
			.filter(v => v.beanData)
			.map(v => v.beanData!);

		// Exclude beans already shown under Saved (saved beans take priority)
		const savedPaths = new Set(
			beans.map(b => b.bean_url_path).filter(Boolean)
		);
		return searchedViewed.filter(
			v => !(v.bean_url_path && savedPaths.has(v.bean_url_path))
		);
	});

	// DEV-only diagnostics: keep per-search console noise out of production.
	$effect(() => {
		if (!import.meta.env.DEV) return;
		const query = debouncedSearchQuery.trim();
		const result = beans;
		const searchedViewed = recentlyViewed;
		if (!query) return;
		console.debug(
			"[vault/saved] search results by section",
			{
				query,
				savedCount: result.length,
				saved: result.map(b => b.bean_url_path),
				recentlyViewedAfterDedupeCount: searchedViewed.length,
				recentlyViewedAfterDedupe: searchedViewed.map(v => v.bean_url_path)
			}
		);
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
		const result: {
			bean: SavedBean;
			isFirstInGroup: boolean;
			groupPeriod: string;
		}[] = [];
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
				bean,
				isFirstInGroup,
				groupPeriod: period,
			});
			lastPeriod = period;
		}

		return result;
	});
</script>

<svelte:head>
	<title>Saved Beans | My Coffee Vault | Kissaten</title>
	<meta
		name="description"
		content="Your saved coffee beans and tasting notes"
	/>
	<meta name="robots" content="noindex,follow" />
	<link rel="canonical" href="https://kissaten.app/vault/saved" />
</svelte:head>

<p
	class="varietal-description-shadow mx-auto mb-8 max-w-3xl text-gray-600 dark:text-cyan-300/80 text-xl text-center"
>
	{#if isLoading}
		Loading your vault...
	{:else if totalSaved === 0}
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
		{#each beansWithGroupLabels as item (item.bean.savedBeanId)}
			<div class="vault-card-slot relative flex flex-col h-full">
				{#if item.isFirstInGroup}
					<div
						class="-top-6 left-0 absolute flex items-center gap-2 font-semibold text-gray-700 dark:text-cyan-300 text-sm whitespace-nowrap"
					>
						<Clock class="w-3.5 h-3.5" />
						{item.groupPeriod}
						<ArrowRight class="opacity-50 w-3.5 h-3.5" />
					</div>
				{/if}
				<div class="h-full">
					<CoffeeBeanCard
						class="h-full"
						bean={item.bean}
						vaultMode={true}
						onNotesChange={(notes) => (item.bean.notes = notes)}
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
					<div class="vault-card-slot">
						<CoffeeBeanCard {bean} />
					</div>
				{/each}
			</div>
		</div>
	{/if}
{/if}