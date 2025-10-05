<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "$lib/components/ui/card/index.js";
	import * as Carousel from "$lib/components/ui/carousel/index.js";
	import { Coffee, Globe, TrendingUp, Search } from "lucide-svelte";
	import { goto } from "$app/navigation";
	import SmartSearch from "$lib/components/search/SmartSearch.svelte";
	import Logo from "$lib/static/logo-alt.svg?raw"
	import CoffeeBeanCard from "$lib/components/CoffeeBeanCard.svelte";
	import RoasterCard from "$lib/components/RoasterCard.svelte";
	import ProcessCard from "$lib/components/ProcessCard.svelte";
	import VarietalCard from "$lib/components/VarietalCard.svelte";
	import { api } from '$lib/api.js';
	import Autoplay from "embla-carousel-autoplay";
	import type { HomePageData } from './+page.ts';
	import { searchStore } from "$lib/stores/search";
	import { onMount } from "svelte";

	interface Props {
		data: {
			dataPromise: Promise<HomePageData>;
		};
	}

	let { data }: Props = $props();

	// Smart Search functionality
	async function performSmartSearch(query: string) {
		await searchStore.performSmartSearch(query);
	}

	async function performImageSearch(image: File) {
		await searchStore.performImageSearch(image);
	}

	onMount(() => {
		searchStore.set({
			...$searchStore,
			smartSearchQuery: "",
		});
	});
</script>

<svelte:head>
	<title>Kissaten - Coffee Bean Discovery Platform</title>
	<meta name="description" content="Discover and explore coffee beans from roasters worldwide" />
</svelte:head>

<div class="mx-auto px-4 py-8 container">
	<!-- Hero Section -->
	<section class="py-16 text-center">
		<h1 class="flex justify-center items-center gap-2 mb-6 font-bold text-4xl md:text-6xl">
			<span class="w-12 md:w-16">{@html Logo}</span> Kissaten
		</h1>
		<p class="mx-auto mb-8 max-w-2xl text-muted-foreground text-xl md:text-2xl">
			Coffee Bean Discovery Platform
		</p>
		<p class="mx-auto mb-12 max-w-3xl text-muted-foreground text-lg">
			Discover and explore coffee beans from roasters worldwide. Search by origin, tasting notes, varietals, processing methods, and more.
		</p>

		<!-- Smart Search - always available immediately -->
		<div class="mx-auto max-w-2xl">
			<SmartSearch
				bind:value={$searchStore.smartSearchQuery}
				loading={$searchStore.smartSearchLoading}
				available={true}
				onSearch={performSmartSearch}
				onImageSearch={performImageSearch}
				autofocus={true}
				showFilterToggleButton={false}
			/>
		</div>

		<!-- Quick Actions -->
		<div class="flex flex-wrap justify-center">
			<Button variant="link" href="/search#advanced-search">
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
					<Carousel.Previous class="hidden md:flex"/>
					<Carousel.Next class="hidden md:flex"/>
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
			<Button variant="outline" href='/roasters'>
				<Globe class="mr-2 w-4 h-4" />
				All Roasters
			</Button>
			<Button variant="outline" href='/countries'>
				<Coffee class="mr-2 w-4 h-4" />
				All Origins
			</Button>
			<Button variant="outline" href='/process'>
				<TrendingUp class="mr-2 w-4 h-4" />
				All Processes
			</Button>
			<Button variant="outline" href='/varietals'>
				<Search class="mr-2 w-4 h-4" />
				All Varietals
			</Button>
		</div>
	</section>
</div>
