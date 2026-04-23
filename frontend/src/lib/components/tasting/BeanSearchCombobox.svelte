<script lang="ts">
	import * as Command from "$lib/components/ui/command";
	import { Button } from "$lib/components/ui/button";
	import { cn, resizeImage } from "$lib/utils";
	import { Search, Loader2, X, Star, History, Sparkles, Camera, Image as ImageIcon } from "lucide-svelte";
	import * as Dialog from "$lib/components/ui/dialog";
	import { onMount } from "svelte";
	import { slide } from "svelte/transition";
	import { api, type CoffeeBean } from "$lib/api";
	import { getRecentlyViewedBeans } from "$lib/db/localdb";
	import { pushState } from "$app/navigation";
	import { page as pageState } from "$app/state";
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
		/** Enable AI smart image search — shows a camera button in the search input */
		enableImageSearch?: boolean;
		/** Pre-loaded country list from layout data, used for origin code → name resolution in image search */
		originOptions?: { value: string; text: string }[];
	}

	let {
		value = $bindable(null),
		beanLabel = $bindable(null),
		selectedBean = $bindable(null),
		savedBeanPaths = [],
		enableImageSearch = false,
		originOptions = []
	}: Props = $props();

	let open = $state(false);
	let searchQuery = $state("");
	let isLoading = $state(false);
	let apiResults = $state<CoffeeBean[]>([]);
	let localSuggestions = $state<CoffeeBean[]>([]);
	let lastParsedParams = $state<any>(null);
	let currentPage = $state(1);
	let hasNextPage = $state(false);

	let isSearchOpen = $derived(open || (!!pageState.state?.searchOpenId && window.innerWidth < 640));

	let savedPage = $state(1);
	let hasMoreSaved = $derived(savedBeanPaths.length > savedPage * 10);

	let isMoreLoading = $state(false);
	let searchTimeout: ReturnType<typeof setTimeout>;

	let listContainer = $state<HTMLDivElement | null>(null);
	let listValue = $state("");
	let containerRef = $state<HTMLDivElement | null>(null);

	// Image search state
	let imageFile = $state<File | null>(null);
	let imagePreview = $state<string | null>(null);
	let imageLoading = $state(false);
	let showImageSourceDialog = $state(false);
	let galleryInputRef = $state<HTMLInputElement | null>(null);
	let cameraInputRef = $state<HTMLInputElement | null>(null);

	// Sync state with history for mobile "go back" behavior
	$effect(() => {
		const isMobile = window.innerWidth < 640;
		const historyId = (pageState.state as any)?.searchOpenId;

		// When opening on mobile, push state if not already there
		if (isMobile && open && !historyId) {
			const newId = Math.random().toString(36).substring(7);
			pushState("", { ...pageState.state, searchOpenId: newId });
			// Once pushed, we rely on page.state.searchOpenId
			open = false;
		}
	});

	$effect(() => {
		function handleClickOutside(e: MouseEvent) {
			if (containerRef && !containerRef.contains(e.target as Node)) {
				handleClose();
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

		const hasMore = hasNextPage || hasMoreSaved;
		if (!hasMore) return;

		// If there is no active search (text or image), only paginate saved beans
		if (!searchQuery && !imagePreview && !hasMoreSaved) return;

		// If text searching, we need at least one source to have more data
		if (searchQuery && !hasNextPage && !hasMoreSaved) return;

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

	async function handleImageFileSelected(file: File) {
		try {
			const resized = await resizeImage(file, 1000, 1000);
			const reader = new FileReader();
			reader.onload = () => { imagePreview = reader.result as string; };
			reader.readAsDataURL(resized);
			imageFile = resized;
			searchQuery = '';
			apiResults = [];
			clearTimeout(searchTimeout);
			await performImageSearch(resized);
		} catch (err) {
			console.error('[BeanSearchCombobox] Image resize error:', err);
		}
	}

	async function performImageSearch(file: File) {
		isLoading = true;
		imageLoading = true;
		open = true;
		try {
			const result = await api.smartImageSearchParameters(file);
			const countryMap = new Map<string, string>(
				originOptions.map(o => [o.value.toUpperCase(), o.text])
			);
			if (result.success && result.searchParams) {
				const p = result.searchParams;
				const origins = (Array.isArray(p.origin) ? p.origin : p.origin ? [p.origin] : [])
					.map(code => countryMap.get(code.toUpperCase()) ?? code);
				// Combine all text-based params into a single FTS query string
				const parts: string[] = [
					p.query,
					p.tasting_notes_query,
					...(Array.isArray(p.roaster) ? p.roaster : p.roaster ? [p.roaster] : []),
					...origins,
					p.region,
					p.producer,
					p.farm,
					p.process,
					p.variety,
					p.roast_level,
				].filter((v): v is string => !!v);
				const fts_query = parts.join(' ');
				searchQuery = fts_query;
				const ftsParams = fts_query ? { fts_query, per_page: 20, page: 1, sort_by: 'relevance' as const } : { per_page: 20, page: 1 };
				const res = await api.search(ftsParams);
				if (res.success && res.data) {
					apiResults = res.data;
					hasNextPage = res.pagination?.has_next ?? false;
					lastParsedParams = ftsParams;
					currentPage = 1;
				}
			} else if (result.rateLimited) {
				console.warn('[BeanSearchCombobox] Image search rate limited');
			}
		} catch (err) {
			console.error('[BeanSearchCombobox] Image search error:', err);
		} finally {
			imageLoading = false;
			isLoading = false;
		}
	}

	function clearImage() {
		imageFile = null;
		imagePreview = null;
		apiResults = [];
		hasNextPage = false;
		lastParsedParams = null;
		currentPage = 1;
		if (galleryInputRef) galleryInputRef.value = '';
		if (cameraInputRef) cameraInputRef.value = '';
	}

	function handleCameraButtonClick() {
		const mobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth < 768;
		if (mobile) {
			showImageSourceDialog = true;
		} else {
			galleryInputRef?.click();
		}
	}

	function handleCameraChoice() {
		showImageSourceDialog = false;
		cameraInputRef?.click();
	}

	function handleGalleryChoice() {
		showImageSourceDialog = false;
		galleryInputRef?.click();
	}

	async function handleImageInput(e: Event & { currentTarget: EventTarget & HTMLInputElement }) {
		const input = e.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		await handleImageFileSelected(file);
		input.value = '';
	}

	function handleSelect(bean: CoffeeBean) {
		const path = bean.bean_url_path || api.getBeanUrlPath(bean);
		value = path;
		selectedBean = bean;
		beanLabel = `${bean.name} · ${bean.roaster}`;

		const isMobile = window.innerWidth < 640;
		const historyId = (pageState.state as any)?.searchOpenId;
		if (isMobile && historyId) {
			window.history.back();
		}

		open = false;
		searchQuery = "";
		apiResults = [];
	}

	function handleTooltipContentClick(e: MouseEvent) {
		// Prevent tooltip content from stealing focus or triggering list item select
		e.stopPropagation();
	}

	function handleClose() {
		const isMobile = window.innerWidth < 640;
		const historyId = (pageState.state as any)?.searchOpenId;
		if (isMobile && historyId) {
			window.history.back();
		}
		open = false;
		searchQuery = '';
		apiResults = [];
		if (enableImageSearch) clearImage();
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
		{#if isSearchOpen}
			<div
				class="sm:hidden z-40 fixed inset-0"
				role="presentation"
				onclick={handleClose}
			/>
		{/if}
		<Tooltip.Provider>
			<div class={cn(
				"border border-emerald-500/20 rounded-md focus-within:ring-2 focus-within:ring-primary ring-offset-background focus-within:ring-offset-2 overflow-hidden transition-all",
				isSearchOpen
					? "max-sm:fixed max-sm:inset-x-0 max-sm:top-0 max-sm:z-50 max-sm:rounded-none max-sm:border-x-0 max-sm:border-t-0 relative w-full sm:focus-within:left-0 sm:focus-within:w-full"
					: "relative w-full sm:focus-within:left-0 focus-within:-left-6 sm:focus-within:w-full focus-within:w-[calc(100vw-3rem)]"
			)} bind:this={containerRef}>
				<Command.Root shouldFilter={false} loop={false} class="**:data-[slot=command-input-wrapper]:border-b-0 border-none">
					<div class="relative bg-emerald-50/10 w-full">
						<Command.Input
							placeholder={imagePreview ? "Refine your image search..." : "Search for an existing bean..."}
							value={searchQuery}
							class={cn("pl-2 border-none focus-visible:ring-0 h-11", enableImageSearch && "pr-10")}
							oninput={(e) => handleSearch(e.currentTarget.value)}
							onfocus={() => (open = true)}
							disabled={imageLoading}
							onkeydown={(e) => {
								if (e.key === 'Escape') {
									handleClose();
								}
							}}
							iconClass={"invisible" /* Hide default icon since we have a custom one */ }
						/>
						<div class="top-1/2 left-3 absolute -translate-y-1/2 pointer-events-none">
							{#if isLoading}
								<Loader2 class="w-4 h-4 text-muted-foreground animate-spin" />
							{:else}
								<Search class="w-4 h-4 text-emerald-500" />
							{/if}
						</div>
						{#if isSearchOpen}
							<button
								type="button"
								onclick={handleClose}
								class="sm:hidden top-1/2 right-3 absolute p-1 -translate-y-1/2"
								aria-label="Close search"
							>
								<X class="w-4 h-4 text-muted-foreground" />
							</button>
						{/if}
						{#if enableImageSearch && !isSearchOpen}
							{#if imagePreview}
								<div class="top-1/2 right-2 absolute flex items-center gap-1 -translate-y-1/2">
									<img src={imagePreview} alt="Preview of selected" class="rounded w-7 h-7 object-cover" />
									<button
										type="button"
										onclick={clearImage}
										class="bg-muted-foreground/20 hover:bg-muted-foreground/40 p-0.5 rounded-full"
										aria-label="Clear selected image"
									>
										<X class="w-3 h-3" />
									</button>
								</div>
							{:else}
								<button
									type="button"
									onclick={handleCameraButtonClick}
									class="top-1/2 right-3 absolute -translate-y-1/2"
									aria-label="Search by image"
								>
									{#if imageLoading}
										<Loader2 class="w-4 h-4 text-muted-foreground animate-spin" />
									{:else}
										<Camera class="w-4 h-4 text-muted-foreground hover:text-foreground" />
									{/if}
								</button>
							{/if}
						{/if}
					</div>
					{#if isSearchOpen}
						<div
							transition:slide={{ duration: 200, axis: 'y' }}
							class={cn(
								"z-50 bg-popover border-t transition-all",
								isSearchOpen && "max-sm:h-[calc(100svh-2.75rem)]"
							)}
							role="presentation"
							onmousedown={(e) => e.preventDefault()}
						>
						<Command.List
							onscroll={handleScroll}
							class="max-h-72 max-sm:max-h-full overflow-x-hidden overflow-y-auto scroll-py-3"
							loop={false}
							shouldFilter={false}
							bind:value={listValue}
						>
							<Command.Empty>
								{#if isLoading}
									<div class="flex justify-center items-center py-6">
										<Loader2 size={24} class="text-muted-foreground animate-spin" />
									</div>
							{:else if imagePreview}
								<p class="py-6 text-sm text-center">No results found for this image.</p>
							{:else if searchQuery.trim().length === 0}
								<p class="py-6 text-sm text-center">Type to search for coffee</p>
							{:else}
								<p class="py-6 text-sm text-center">No beans found for "{searchQuery}"</p>
							{/if}
						</Command.Empty>

						{#if suggestions.length > 0}
							<Command.Group heading="Recently Viewed & Saved" class="[&_[data-command-group-items]]:flex [&_[data-command-group-items]]:flex-col p-0">
								{#each suggestions as bean}
									<Tooltip.Root delayDuration={300}>
										<Tooltip.Trigger asChild>
											{#snippet children({ props })}
												<Command.Item
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
								<Command.Group heading={imagePreview ? "Image Search Results" : "Search Results"} class="[&_[data-command-group-items]]:flex [&_[data-command-group-items]]:flex-col p-0">
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
		{#if enableImageSearch}
			<input
				type="file"
				bind:this={galleryInputRef}
				oninput={handleImageInput}
				class="hidden"
				accept="image/jpeg,image/png,image/webp,image/avif"
			/>
			<input
				type="file"
				bind:this={cameraInputRef}
				oninput={handleImageInput}
				class="hidden"
				accept="image/jpeg,image/png,image/webp,image/avif"
				capture="environment"
			/>
			<Dialog.Root bind:open={showImageSourceDialog}>
				<Dialog.Content class="sm:max-w-md">
					<Dialog.Header>
						<Dialog.Title>Choose Image Source</Dialog.Title>
						<Dialog.Description>
							Select where you'd like to get your image from
						</Dialog.Description>
					</Dialog.Header>
					<div class="flex flex-col gap-3 py-4">
						<Button
							onclick={handleCameraChoice}
							variant="default"
							class="w-full h-16 text-lg"
						>
							<Camera class="mr-2 w-5 h-5" />
							Take Photo
						</Button>
						<Button
							onclick={handleGalleryChoice}
							variant="secondary"
							class="w-full h-16 text-lg"
						>
							<ImageIcon class="mr-2 w-5 h-5" />
							Choose from Gallery
						</Button>
					</div>
				</Dialog.Content>
			</Dialog.Root>
		{/if}
		</Tooltip.Provider>
	{/if}
</div>
