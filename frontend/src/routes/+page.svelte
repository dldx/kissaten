<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "$lib/components/ui/card/index.js";
	import * as Carousel from "$lib/components/ui/carousel/index.js";
	import { Coffee, Globe, TrendingUp, Search } from "lucide-svelte";
	import { goto } from "$app/navigation";
	import AISearch from "$lib/components/search/AISearch.svelte";
	import SearchBar from "$lib/components/search/SearchBar.svelte";
	import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
	import RoasterCard from "$lib/components/RoasterCard.svelte";
	import ProcessCard from "$lib/components/ProcessCard.svelte";
	import VarietalCard from "$lib/components/VarietalCard.svelte";
	import { api } from '$lib/api.js';
	import Autoplay from "embla-carousel-autoplay";
	import type { HomePageData } from './+page.ts';

	interface Props {
		data: {
			dataPromise: Promise<HomePageData>;
		};
	}

	let { data }: Props = $props();

	let searchQuery = $state("");
	let aiSearchQuery = $state("");
	let aiSearchLoading = $state(false);

	// AI Search functionality
	async function performAISearch() {
		if (!aiSearchQuery) return;

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
				if (searchParams.origin) {
					const countries = Array.isArray(searchParams.origin) ? searchParams.origin : [searchParams.origin];
					countries.forEach(c => params.append('country', c));
				}
				if (searchParams.region) params.set('region', searchParams.region);
				if (searchParams.producer) params.set('producer', searchParams.producer);
				if (searchParams.farm) params.set('farm', searchParams.farm);
				if (searchParams.roast_level) params.set('roast_level', searchParams.roast_level);
				if (searchParams.roast_profile) params.set('roast_profile', searchParams.roast_profile);
				if (searchParams.process) params.set('process', searchParams.process);
				if (searchParams.variety) params.set('variety', searchParams.variety);
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

				// Add the original smart query to preserve it on the search page
				params.set('smart_query', aiSearchQuery);

				const searchUrl = `/search${params.toString() ? '?' + params.toString() : ''}`;
				goto(searchUrl);
			} else {
				// AI search failed, fall back to regular search
				if (aiSearchQuery.trim()) {
					const fallbackParams = new URLSearchParams();
					fallbackParams.set('q', aiSearchQuery.trim());
					fallbackParams.set('smart_query', aiSearchQuery);
					goto(`/search?${fallbackParams.toString()}`);
				}
			}

		} catch (err) {
			console.error('AI search error:', err);
			// Fall back to regular search
			if (aiSearchQuery.trim()) {
				const fallbackParams = new URLSearchParams();
				fallbackParams.set('q', aiSearchQuery.trim());
				fallbackParams.set('smart_query', aiSearchQuery);
				goto(`/search?${fallbackParams.toString()}`);
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

		<!-- AI Search - always available immediately -->
		<div class="mx-auto max-w-2xl">
			<AISearch
				bind:value={aiSearchQuery}
				loading={aiSearchLoading}
				available={true}
				onSearch={performAISearch}
				autofocus={true}
			/>
		</div>

		<!-- Quick Actions -->
		<div class="flex flex-wrap justify-center">
			<Button variant="link" onclick={() => goto('/search#advanced-search')}>
				<TrendingUp class="mr-2 w-4 h-4" />
				Advanced Search
			</Button>
		</div>
	</section>

	<!-- Carousel Section -->
	<section class="py-16">
		<h2 class="mb-12 font-[family-name:var(--font-fun)] font-normal text-3xl text-center">Discover Coffee</h2>

		{#await data.dataPromise}
			<!-- Loading state -->
			<div class="mx-auto w-full max-w-7xl">
				<div class="gap-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
					{#each Array(8) as _, i}
						<Card class="h-[400px]">
							<CardContent class="flex justify-center items-center h-full">
								<div class="border-gray-900 border-b-2 rounded-full w-8 h-8 animate-spin"></div>
							</CardContent>
						</Card>
					{/each}
				</div>
			</div>
		{:then homeData}
			{#if homeData.carouselItems.length > 0}
				<Carousel.Root
					opts={{
						align: "start",
						loop: true,
					}}
					plugins={[Autoplay({ delay: 3000, stopOnInteraction: true })]}
					class="mx-auto w-full max-w-7xl"
				>
					<Carousel.Content>
						{#each homeData.carouselItems as item (item.key)}
							<Carousel.Item class="md:basis-1/2 lg:basis-1/3 xl:basis-1/4">
								<div class="p-2">
									{#if item.type === 'bean'}
										<a
											class="w-full text-left"
											href={`/roasters${item.data.bean_url_path}`}
										>
											<CoffeeBeanCard bean={item.data} class="h-full" />
										</a>
									{:else if item.type === 'roaster'}
										<RoasterCard roaster={item.data} />
									{:else if item.type === 'process'}
										<ProcessCard process={item.data} />
									{:else if item.type === 'varietal'}
										<VarietalCard varietal={item.data} />
									{/if}
								</div>
							</Carousel.Item>
						{/each}
					</Carousel.Content>
					<Carousel.Previous />
					<Carousel.Next />
				</Carousel.Root>
			{:else}
				<!-- Empty state -->
				<div class="mx-auto w-full max-w-7xl">
					<div class="gap-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
						{#each Array(8) as _, i}
							<Card class="h-[400px]">
								<CardContent class="flex justify-center items-center h-full">
									<p class="text-muted-foreground">No data available</p>
								</CardContent>
							</Card>
						{/each}
					</div>
				</div>
			{/if}
		{:catch error}
			<!-- Error state -->
			<div class="mx-auto w-full max-w-7xl">
				<Card class="h-[400px]">
					<CardContent class="flex justify-center items-center h-full">
						<p class="text-muted-foreground">Failed to load carousel data</p>
					</CardContent>
				</Card>
			</div>
		{/await}

		<!-- Quick Navigation -->
		<div class="flex flex-wrap justify-center gap-4 mt-8">
			<Button variant="outline" onclick={() => goto('/roasters')}>
				<Globe class="mr-2 w-4 h-4" />
				All Roasters
			</Button>
			<Button variant="outline" onclick={() => goto('/countries')}>
				<Coffee class="mr-2 w-4 h-4" />
				All Origins
			</Button>
			<Button variant="outline" onclick={() => goto('/process')}>
				<TrendingUp class="mr-2 w-4 h-4" />
				All Processes
			</Button>
			<Button variant="outline" onclick={() => goto('/varietals')}>
				<Search class="mr-2 w-4 h-4" />
				All Varietals
			</Button>
		</div>
	</section>
</div>
