<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "$lib/components/ui/card/index.js";
	import { Coffee, Globe, TrendingUp, Search } from "lucide-svelte";
	import { goto } from "$app/navigation";
	import { onMount } from 'svelte';
	import AISearch from "$lib/components/search/AISearch.svelte";
	import SearchBar from "$lib/components/search/SearchBar.svelte";
	import { api } from '$lib/api.js';

	let searchQuery = $state("");
	let aiSearchQuery = $state("");
	let aiSearchLoading = $state(false);
	let aiSearchAvailable = $state(true);

	// Check if AI search is available
	onMount(async () => {
		try {
			const response = await api.aiSearchHealth();
			aiSearchAvailable = response.success;
		} catch (error) {
			console.warn('AI search service not available:', error);
			aiSearchAvailable = false;
		}
	});

	// AI Search functionality
	async function performAISearch() {
		if (!aiSearchQuery || !aiSearchAvailable) return;

		try {
			aiSearchLoading = true;

			// Use the AI search to get parsed parameters
			const aiResult = await api.aiSearchParameters(aiSearchQuery);

			if (aiResult.success && aiResult.searchParams) {
				// Navigate to search page with AI-generated parameters
				const params = new URLSearchParams();
				const searchParams = aiResult.searchParams;

				// Add all the parameters to the URL
				if (searchParams.query) params.set('q', searchParams.query);
				if (searchParams.tasting_notes_query) params.set('tasting_notes_query', searchParams.tasting_notes_query);
				if (searchParams.roaster) {
					const roasters = Array.isArray(searchParams.roaster) ? searchParams.roaster : [searchParams.roaster];
					roasters.forEach(r => params.append('roaster', r));
				}
				if (searchParams.roaster_location) {
					const locations = Array.isArray(searchParams.roaster_location) ? searchParams.roaster_location : [searchParams.roaster_location];
					locations.forEach(rl => params.append('roaster_location', rl));
				}
				if (searchParams.country) {
					const countries = Array.isArray(searchParams.country) ? searchParams.country : [searchParams.country];
					countries.forEach(c => params.append('country', c));
				}
				if (searchParams.region) {
					const regions = Array.isArray(searchParams.region) ? searchParams.region : [searchParams.region];
					regions.forEach(r => params.append('region', r));
				}
				if (searchParams.producer) {
					const producers = Array.isArray(searchParams.producer) ? searchParams.producer : [searchParams.producer];
					producers.forEach(p => params.append('producer', p));
				}
				if (searchParams.farm) {
					const farms = Array.isArray(searchParams.farm) ? searchParams.farm : [searchParams.farm];
					farms.forEach(f => params.append('farm', f));
				}
				if (searchParams.roast_level) params.set('roast_level', searchParams.roast_level);
				if (searchParams.roast_profile) params.set('roast_profile', searchParams.roast_profile);
				if (searchParams.process) {
					const processes = Array.isArray(searchParams.process) ? searchParams.process : [searchParams.process];
					processes.forEach(p => params.append('process', p));
				}
				if (searchParams.variety) {
					const varieties = Array.isArray(searchParams.variety) ? searchParams.variety : [searchParams.variety];
					varieties.forEach(v => params.append('variety', v));
				}
				if (searchParams.min_price) params.set('min_price', searchParams.min_price.toString());
				if (searchParams.max_price) params.set('max_price', searchParams.max_price.toString());
				if (searchParams.min_weight) params.set('min_weight', searchParams.min_weight.toString());
				if (searchParams.max_weight) params.set('max_weight', searchParams.max_weight.toString());
				if (searchParams.min_elevation) params.set('min_elevation', searchParams.min_elevation.toString());
				if (searchParams.max_elevation) params.set('max_elevation', searchParams.max_elevation.toString());
				if (searchParams.in_stock_only) params.set('in_stock_only', 'true');
				if (searchParams.is_decaf !== undefined && searchParams.is_decaf !== null) params.set('is_decaf', searchParams.is_decaf.toString());
				if (searchParams.is_single_origin !== undefined && searchParams.is_single_origin !== null) params.set('is_single_origin', searchParams.is_single_origin.toString());
				if (searchParams.sort_by && searchParams.sort_by !== 'name') params.set('sort_by', searchParams.sort_by);
				if (searchParams.sort_order && searchParams.sort_order !== 'asc') params.set('sort_order', searchParams.sort_order);

				const searchUrl = `/search${params.toString() ? '?' + params.toString() : ''}`;
				goto(searchUrl);
			} else {
				// AI search failed, fall back to regular search
				if (aiSearchQuery.trim()) {
					goto(`/search?q=${encodeURIComponent(aiSearchQuery.trim())}`);
				}
			}

		} catch (err) {
			console.error('AI search error:', err);
			// Fall back to regular search
			if (aiSearchQuery.trim()) {
				goto(`/search?q=${encodeURIComponent(aiSearchQuery.trim())}`);
			}
		} finally {
			aiSearchLoading = false;
		}
	}
</script>

<svelte:head>
	<title>Kissaten - Coffee Bean Discovery Platform</title>
	<meta name="description" content="Discover and explore coffee beans from roasters worldwide" />
</svelte:head>

<div class="mx-auto px-4 py-8 container">
	<!-- Hero Section -->
	<section class="py-16 text-center">
		<h1 class="mb-6 font-bold text-4xl md:text-6xl">
			☕ Kissaten
		</h1>
		<p class="mx-auto mb-8 max-w-2xl text-muted-foreground text-xl md:text-2xl">
			Coffee Bean Discovery Platform
		</p>
		<p class="mx-auto mb-12 max-w-3xl text-muted-foreground text-lg">
			Discover and explore coffee beans from roasters worldwide. Search by origin, tasting notes, processing methods, and more.
		</p>

		<!-- AI Search -->
		{#if aiSearchAvailable}
			<div class="mx-auto mb-4 max-w-2xl">
				<AISearch
					bind:value={aiSearchQuery}
					loading={aiSearchLoading}
					available={aiSearchAvailable}
					onSearch={performAISearch}
				/>
			</div>
		{/if}

		<!-- Quick Actions -->
		<div class="flex flex-wrap justify-center gap-4">
			<Button variant="outline" onclick={() => goto('/search')}>
				<TrendingUp class="mr-2 w-4 h-4" />
				Advanced Search
			</Button>
		</div>
	</section>

	<!-- Features Section -->
	<section class="py-16">
		<h2 class="mb-12 font-[family-name:var(--font-fun)] font-normal text-3xl text-center">Explore Coffee Beans</h2>
		<div class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
			<Card>
				<CardHeader>
					<CardTitle class="flex items-center font-[family-name:var(--font-heading)]">
						<Coffee class="mr-2 w-5 h-5" />
						Browse by Roaster
					</CardTitle>
					<CardDescription>
						Discover coffee beans from your favorite roasters around the world
					</CardDescription>
				</CardHeader>
				<CardContent>
					<p class="mb-4 text-muted-foreground text-sm">
						Explore beans from specialty roasters including A.M.O.C., Cartwheel Coffee, Drop Coffee, and many more.
					</p>
					<Button variant="outline" class="w-full" onclick={() => goto('/roasters')}>
						View All Roasters
					</Button>
				</CardContent>
			</Card>

			<Card>
				<CardHeader>
					<CardTitle class="flex items-center font-[family-name:var(--font-heading)]">
						<Globe class="mr-2 w-5 h-5" />
						Browse by Origin
					</CardTitle>
					<CardDescription>
						Find beans from specific countries and regions
					</CardDescription>
				</CardHeader>
				<CardContent>
					<p class="mb-4 text-muted-foreground text-sm">
						Search for beans from Brazil, Colombia, Ethiopia, Guatemala, and other coffee-growing regions.
					</p>
					<Button variant="outline" class="w-full" onclick={() => goto('/countries')}>
						Explore Origins
					</Button>
				</CardContent>
			</Card>

			<Card>
				<CardHeader>
					<CardTitle class="flex items-center font-[family-name:var(--font-heading)]">
						<Search class="mr-2 w-5 h-5" />
						Unified Search
					</CardTitle>
					<CardDescription>
						Search across beans, roasters, and tasting notes
					</CardDescription>
				</CardHeader>
				<CardContent>
					<p class="mb-4 text-muted-foreground text-sm">
						Find exactly what you're looking for with our powerful search that covers all aspects of coffee beans.
					</p>
					<Button variant="outline" class="w-full" onclick={() => goto('/search')}>
						Advanced Search
					</Button>
				</CardContent>
			</Card>
		</div>
	</section>
</div>
