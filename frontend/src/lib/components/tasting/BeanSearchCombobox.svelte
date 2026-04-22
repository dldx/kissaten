<script lang="ts">
	import * as Command from "$lib/components/ui/command";
	import { Button } from "$lib/components/ui/button";
	import { cn } from "$lib/utils";
	import { Search, Loader2, X, Star, History, Sparkles } from "lucide-svelte";
	import { onMount } from "svelte";
	import { slide } from "svelte/transition";
	import { api, type CoffeeBean } from "$lib/api";
	import { getRecentlyViewedBeans } from "$lib/db/localdb";
	import CoffeeBeanCard from "../CoffeeBeanCard.svelte";
	import CoffeeBeanTile from "./CoffeeBeanTile.svelte";
	import * as Tooltip from "$lib/components/ui/tooltip";

	interface Props {
		/** The bean_url_path of the selected bean */
		value: string | null | undefined;
		/** The human-readable name/label of the bean */
		beanLabel: string | null | undefined;
		/** The full selected bean object */
		selectedBean?: CoffeeBean | null;
		/** List of bean_url_paths that the user has saved (passed from page load) */
		savedBeanPaths?: string[];
	}

	let {
		value = $bindable(null),
		beanLabel = $bindable(null),
		selectedBean = $bindable(null),
		savedBeanPaths = []
	}: Props = $props();

	let open = $state(false);
	let searchQuery = $state("");
	let isLoading = $state(false);
	let apiResults = $state<CoffeeBean[]>([]);
	let localSuggestions = $state<CoffeeBean[]>([]);
	let lastParsedParams = $state<any>(null);
	let currentPage = $state(1);
	let hasNextPage = $state(false);

	let savedPage = $state(1);
	let hasMoreSaved = $derived(savedBeanPaths.length > savedPage * 10);

	let isMoreLoading = $state(false);
	let searchTimeout: ReturnType<typeof setTimeout>;

	let listContainer = $state<HTMLDivElement | null>(null);
	let listValue = $state("");
	let containerRef = $state<HTMLDivElement | null>(null);

	$effect(() => {
		function handleClickOutside(e: MouseEvent) {
			if (containerRef && !containerRef.contains(e.target as Node)) {
				open = false;
			}
		}
		document.addEventListener('mousedown', handleClickOutside);
		return () => document.removeEventListener('mousedown', handleClickOutside);
	});

	onMount(async () => {
		console.log(`[BeanSearchCombobox] onMount. value: ${value}`);
		isLoading = true;
		try {
			// If we have a value but no selectedBean, try to fetch it
			if (value && !selectedBean) {
				const res = await api.searchBeansByPaths([value]);
				if (res.success && res.data && res.data.length > 0) {
					console.log(`[BeanSearchCombobox] Fetched selectedBean: ${res.data[0].name}`);
					selectedBean = res.data[0];
				}
			}

			// 1. Get recently viewed
			const recent = await getRecentlyViewedBeans();
			const recentBeans = recent.slice(0, 10).map((r) => r.beanData);
			console.log(`[BeanSearchCombobox] Recently viewed count: ${recentBeans.length}`);

			// Deduplicate by URL path (including initial recent beans)
			const seen = new Set<string>();
			localSuggestions = recentBeans.filter((b) => {
				const path = b.bean_url_path || api.getBeanUrlPath(b);
				if (seen.has(path)) return false;
				seen.add(path);
				return true;
			});
			console.log(`[BeanSearchCombobox] Initial localSuggestions: ${localSuggestions.length}`);
		} finally {
			isLoading = false;
		}
	});

	// Reactively fetch saved beans whenever savedBeanPaths changes
	$effect(() => {
		if (savedBeanPaths.length === 0) return;

		console.log(`[BeanSearchCombobox] savedBeanPaths updated: count ${savedBeanPaths.length}`);

		(async () => {
			try {
				console.log(`[BeanSearchCombobox] Fetching saved beans for paths:`, savedBeanPaths.slice(0, 10));
				const savedRes = await api.searchBeansByPaths(savedBeanPaths.slice(0, 10));

				if (savedRes.success && savedRes.data) {
					const savedBeans = savedRes.data;
					console.log(`[BeanSearchCombobox] Successfully fetched saved beans: ${savedBeans.length}`);

					// Merge with existing suggestions and deduplicate
					const combined = [...localSuggestions, ...savedBeans];
					const seen = new Set<string>();
					localSuggestions = combined.filter((b) => {
						const path = b.bean_url_path || api.getBeanUrlPath(b);
						if (seen.has(path)) return false;
						seen.add(path);
						return true;
					});
					console.log(`[BeanSearchCombobox] Updated localSuggestions (deduplicated): ${localSuggestions.length}`);
				} else {
					console.warn(`[BeanSearchCombobox] Failed to fetch saved beans:`, savedRes.error);
				}
			} catch (err) {
				console.error(`[BeanSearchCombobox] Error in saved beans effect:`, err);
			}
		})();
	});

	async function handleSearch(query: string) {
		searchQuery = query;
		clearTimeout(searchTimeout);

		if (query.trim().length < 2) {
			apiResults = [];
			currentPage = 1;
			hasNextPage = false;
			return;
		}

		console.log(`[BeanSearchCombobox] Triggering FTS search for: ${query}`);
		searchTimeout = setTimeout(async () => {
			isLoading = true;
			currentPage = 1;
			try {
				const res = await api.search({
					fts_query: query,
					per_page: 20,
					page: 1,
					sort_by: 'relevance'
				});

				console.log(`[BeanSearchCombobox] FTS results received:`, res.data?.length);
				if (res.success && res.data) {
					apiResults = res.data;
					hasNextPage = res.pagination?.has_next ?? false;
					lastParsedParams = { fts_query: query };
				}
			} catch (err) {
				console.error(`[BeanSearchCombobox] FTS search error:`, err);
			} finally {
				isLoading = false;
			}
		}, 600); // Shorter debounce for FTS
	}

	async function loadMore() {
		if (isMoreLoading) return;

		// If searching, we need at least one source to have more data
		if (searchQuery && !hasNextPage && !hasMoreSaved) return;

		// If NOT searching, we only care about more saved beans
		if (!searchQuery && !hasMoreSaved) return;

		isMoreLoading = true;

		try {
			// Handle more saved beans if they exist
			if (hasMoreSaved) {
				const nextSavedPage = savedPage + 1;
				const pathsToFetch = savedBeanPaths.slice(savedPage * 10, nextSavedPage * 10);
				console.log(`[BeanSearchCombobox] Loading more saved beans:`, pathsToFetch);

				const savedRes = await api.searchBeansByPaths(pathsToFetch);
				if (savedRes.success && savedRes.data) {
					const combined = [...localSuggestions, ...savedRes.data];
					const seen = new Set<string>();
					localSuggestions = combined.filter((b) => {
						const path = b.bean_url_path || api.getBeanUrlPath(b);
						if (seen.has(path)) return false;
						seen.add(path);
						return true;
					});
					savedPage = nextSavedPage;
				}
			}

			// Handle more API results if they exist
			if (hasNextPage) {
				const nextPage = currentPage + 1;
				// Use the cached parameters if available, otherwise fallback to query
				let searchParams = lastParsedParams || { query: searchQuery };

				console.log(`[BeanSearchCombobox] Loading more API results with params:`, searchParams, `page: ${nextPage}`);

				const res = await api.search({
					...searchParams,
					per_page: 20,
					page: nextPage,
					sort_by: searchParams.fts_query ? 'relevance' : undefined
				});
				if (res.success && res.data) {
					apiResults = [...apiResults, ...res.data];
					currentPage = nextPage;
					hasNextPage = res.pagination?.has_next ?? false;
				}
			}
		} catch (err) {
			console.error(`[BeanSearchCombobox] Load more error:`, err);
		} finally {
			isMoreLoading = false;
		}
	}

	function handleScroll(e: Event) {
		const target = e.currentTarget as HTMLElement;
		const threshold = 100; // px from bottom
		if (
			target.scrollHeight - target.scrollTop - target.clientHeight < threshold &&
			(hasNextPage || hasMoreSaved) &&
			!isMoreLoading
		) {
			loadMore();
		}
	}

	function handleSelect(bean: CoffeeBean) {
		const path = bean.bean_url_path || api.getBeanUrlPath(bean);
		value = path;
		selectedBean = bean;
		beanLabel = `${bean.name} · ${bean.roaster}`;
		open = false;
		searchQuery = "";
		apiResults = [];
	}

	function handleTooltipContentClick(e: MouseEvent) {
		// Prevent tooltip content from stealing focus or triggering list item select
		e.stopPropagation();
	}

	function clear() {
		value = null;
		beanLabel = null;
		selectedBean = null;
	}

	const suggestions = $derived.by(() => {
		if (!searchQuery) return localSuggestions;
		const query = searchQuery.toLowerCase();
		return localSuggestions.filter((b) =>
			b.name.toLowerCase().includes(query) ||
			b.roaster.toLowerCase().includes(query) ||
			(b.origins && b.origins.some(o => o.country.toLowerCase().includes(query))) ||
			(b.varietal && b.varietal.toLowerCase().includes(query)) ||
			(b.process && b.process.toLowerCase().includes(query))
		);
	});
</script>

<div class="w-full min-w-0">
	{#if value}
		<div class="group relative min-w-0">
			<CoffeeBeanTile bean={selectedBean} label={beanLabel} noLink />
			<Button
				variant="ghost"
				size="icon"
				class="top-2 right-2 absolute hover:bg-destructive/10 opacity-40 hover:opacity-100 rounded-full w-7 h-7 hover:text-destructive transition-all shrink-0"
				onclick={clear}
			>
				<X size={14} />
			</Button>
		</div>
	{:else}
		<Tooltip.Provider>
			<div class="sm:focus-within:left-0 focus-within:-left-8 relative border border-emerald-500/20 rounded-md focus-within:ring-2 focus-within:ring-primary ring-offset-background focus-within:ring-offset-2 w-full sm:focus-within:w-full focus-within:w-[calc(100vw-4rem)] overflow-hidden transition-all" bind:this={containerRef}>
				<Command.Root shouldFilter={false} loop={false} class="**:data-[slot=command-input-wrapper]:border-b-0 border-none">
					<div class="relative bg-emerald-50/10 w-full">
						<Command.Input
							placeholder="Search for an existing bean..."
							value={searchQuery}
							class="pl-2 border-none focus-visible:ring-0 h-11"
							oninput={(e) => handleSearch(e.currentTarget.value)}
							onfocus={() => (open = true)}

							onkeydown={(e) => {
								if (e.key === 'Escape') {
									open = false;
									searchQuery = '';
									apiResults = [];
								}
							}}
						/>
						<div class="top-1/2 left-3 absolute -translate-y-1/2 pointer-events-none">
							{#if isLoading}
								<Loader2 class="w-4 h-4 text-muted-foreground animate-spin" />
							{:else}
								<Search class="w-4 h-4 text-emerald-500" />
							{/if}
						</div>
					</div>
					{#if open}
						<div
							transition:slide={{ duration: 200, axis: 'y' }}
							class="z-50 bg-popover border-t"
							role="presentation"
							onmousedown={(e) => e.preventDefault()}
						>
						<Command.List
							onscroll={handleScroll}
							class="max-h-72 overflow-x-hidden overflow-y-auto scroll-py-3"
							loop={false}
							shouldFilter={false}
							bind:value={listValue}
						>
							<Command.Empty>
								{#if isLoading}
									<div class="flex justify-center items-center py-6">
										<Loader2 size={24} class="text-muted-foreground animate-spin" />
									</div>
                                {:else if searchQuery.trim().length == 0}
                                Type to search for coffee

								{:else}
									No beans found for "{searchQuery}"
								{/if}
							</Command.Empty>

							{#if suggestions.length > 0}
								<Command.Group heading="Recently Viewed & Saved" class="[&_[data-command-group-items]]:flex [&_[data-command-group-items]]:flex-col p-0">
									{#each suggestions as bean}
										<Tooltip.Root delayDuration={300}>
											<Tooltip.Trigger asChild>
												{#snippet children({ props })}
													<Command.Item
														{...props}
														value={bean.name + " " + bean.roaster + " " + (bean.bean_url_path || "")}
														onSelect={() => handleSelect(bean)}
														class="p-0 rounded-none w-full"
													>
														<CoffeeBeanTile {bean} slim size="sm" noLink class="bg-transparent hover:bg-muted/50 border-none rounded-none w-full" />
													</Command.Item>
												{/snippet}
											</Tooltip.Trigger>
											<Tooltip.Content
												side="right"
												class="hidden sm:block bg-transparent shadow-none p-0 border-none"
												sideOffset={10}
												onmousedown={handleTooltipContentClick}
											>
												<div class="w-80 pointer-events-none">
													<CoffeeBeanCard {bean} />
												</div>
											</Tooltip.Content>
										</Tooltip.Root>
									{/each}
								</Command.Group>
							{/if}

							{#if apiResults.length > 0}
								<Command.Group heading="Search Results" class="[&_[data-command-group-items]]:flex [&_[data-command-group-items]]:flex-col p-0">
									{#each apiResults as bean}
										{#if !suggestions.some(s => (s.bean_url_path || api.getBeanUrlPath(s)) === (bean.bean_url_path || api.getBeanUrlPath(bean)))}
											<Tooltip.Root delayDuration={300}>
												<Tooltip.Trigger asChild>
													{#snippet children({ props })}
														<Command.Item
															{...props}
															value={bean.name + " " + bean.roaster + " " + (bean.bean_url_path || "")}
															onSelect={() => handleSelect(bean)}
															class="p-0 rounded-none w-full"
														>
															<CoffeeBeanTile {bean} slim size="sm" noLink class="bg-transparent hover:bg-muted/50 border-none rounded-none w-full" />
														</Command.Item>
													{/snippet}
												</Tooltip.Trigger>
												<Tooltip.Content
													side="right"
													class="hidden sm:block bg-transparent shadow-none p-0 border-none"
													sideOffset={10}
													onmousedown={handleTooltipContentClick}
												>
													<div class="w-80 pointer-events-none">
														<CoffeeBeanCard {bean} />
													</div>
												</Tooltip.Content>
											</Tooltip.Root>
										{/if}
									{/each}
									{#if isMoreLoading}
										<div class="flex justify-center py-4">
											<Loader2 size={20} class="text-muted-foreground animate-spin" />
										</div>
									{/if}
								</Command.Group>
							{/if}
						</Command.List>
						</div>
					{/if}
				</Command.Root>
			</div>
		</Tooltip.Provider>
	{/if}
</div>
