<script lang="ts">
	import { goto } from '$app/navigation';
	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "$lib/components/ui/card/index.js";
	import { Coffee, MapPin, Search, ExternalLink } from "lucide-svelte";
	import { type Roaster } from '$lib/api.js';
	import type { PageData } from './$types';

	interface Props {
		data: PageData;
	}

	let { data }: Props = $props();

	let roasters: Roaster[] = $state(data.roasters);
	let filteredRoasters: Roaster[] = $state(data.roasters);
	let searchQuery = $state('');

	function filterRoasters() {
		if (!searchQuery.trim()) {
			filteredRoasters = roasters;
		} else {
			const query = searchQuery.toLowerCase();
			filteredRoasters = roasters.filter(roaster =>
				roaster.name.toLowerCase().includes(query) ||
				roaster.location.toLowerCase().includes(query)
			);
		}
	}

	function viewRoasterBeans(roasterName: string) {
		goto(`/search?roaster=${encodeURIComponent(roasterName)}`);
	}

	$effect(() => {
		filterRoasters();
	});
</script>

<svelte:head>
	<title>Coffee Roasters - Kissaten</title>
	<meta name="description" content="Browse coffee roasters from around the world" />
</svelte:head>

<div class="mx-auto px-4 py-8 container">
	<!-- Header -->
	<div class="mb-12 text-center">
		<h1 class="mb-4 font-bold text-4xl">Coffee Roasters</h1>
		<p class="mx-auto max-w-2xl text-muted-foreground text-xl">
			Discover specialty coffee roasters from around the world and explore their unique bean selections.
		</p>
	</div>

	<!-- Search Bar -->
	<div class="mx-auto mb-8 max-w-md">
		<div class="relative">
			<Search class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
			<Input
				bind:value={searchQuery}
				placeholder="Search roasters..."
				class="pl-10"
			/>
		</div>
	</div>

	<!-- Roasters Grid -->
	{#if filteredRoasters}
		<div class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 mb-8">
			{#each filteredRoasters as roaster (roaster.id)}
				<Card class="flex flex-col hover:shadow-lg h-full transition-shadow">
					<CardHeader>
						<CardTitle class="flex justify-between items-center">
							<span>{roaster.name}</span>
							{#if roaster.website}
								<Button
									variant="ghost"
									size="sm"
									onclick={() => window.open(roaster.website, '_blank')}
								>
									<ExternalLink class="w-4 h-4" />
								</Button>
							{/if}
						</CardTitle>
						{#if roaster.location}
							<CardDescription class="flex items-center">
								<MapPin class="mr-1 w-4 h-4" />
								{roaster.location}
							</CardDescription>
						{/if}
					</CardHeader>
					<CardContent class="flex flex-col flex-grow">
						<div class="flex flex-col flex-grow justify-center items-center space-y-1">
							<img src="/static/data/roasters/{roaster.slug}/logo.png" alt="{roaster.name} Logo" class="w-36" />

							{#if roaster.last_scraped}
								<div class="text-muted-foreground text-xs">
									Last updated: {new Date(roaster.last_scraped).toLocaleDateString()}
								</div>
							{/if}
						</div>

						<div class="mt-auto pt-4">
							<Button
								class="w-full"
								variant="outline"
								onclick={() => viewRoasterBeans(roaster.name)}
							>
								<Coffee class="mr-2 w-4 h-4" />
								View Beans ({roaster.current_beans_count})
							</Button>
						</div>
					</CardContent>
				</Card>
			{/each}
		</div>

		<!-- Results Summary -->
		<div class="text-muted-foreground text-center">
			Showing {filteredRoasters.length} of {roasters.length} roasters
		</div>
	{/if}

	<!-- Empty State -->
	{#if filteredRoasters && filteredRoasters.length === 0 && searchQuery}
		<div class="py-12 text-center">
			<Coffee class="mx-auto mb-4 w-12 h-12 text-muted-foreground" />
			<h3 class="mb-2 font-semibold text-xl">No roasters found</h3>
			<p class="mb-4 text-muted-foreground">Try searching with different keywords.</p>
			<Button onclick={() => searchQuery = ''}>Clear Search</Button>
		</div>
	{/if}
</div>
