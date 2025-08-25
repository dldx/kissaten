<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "$lib/components/ui/card/index.js";
	import { Globe, Coffee, Search, MapPin } from "lucide-svelte";
	import { api, type Country, type CountryCode } from '$lib/api.js';
	import { getCountryFlag } from '$lib/utils.js';

	let countries: Country[] = $state([]);
	let countryCodes: CountryCode[] = $state([]);
	let filteredCountries: Country[] = $state([]);
	let loading = $state(true);
	let error = $state('');
	let searchQuery = $state('');


	onMount(async () => {
		try {
			const [countriesResponse, countryCodesResponse] = await Promise.all([
				api.getCountries(),
				api.getCountryCodes()
			]);

			if (countriesResponse.success && countriesResponse.data) {
				countries = countriesResponse.data;
				filteredCountries = countries;
			} else {
				error = countriesResponse.message || 'Failed to load countries';
			}

			if (countryCodesResponse.success && countryCodesResponse.data) {
				countryCodes = countryCodesResponse.data;
			}
		} catch (err) {
			error = err instanceof Error ? err.message : 'An error occurred';
		} finally {
			loading = false;
		}
	});

	function filterCountries() {
		if (!searchQuery.trim()) {
			filteredCountries = countries;
		} else {
			const query = searchQuery.toLowerCase();
			filteredCountries = countries.filter(country =>
				country.country_name.toLowerCase().includes(query) ||
				country.country_code.toLowerCase().includes(query)
			);
		}
	}

	function viewCountryBeans(countryCode: string) {
		goto(`/search?country=${encodeURIComponent(countryCode)}`);
	}

	$effect(() => {
		filterCountries();
	});
</script>

<svelte:head>
	<title>Coffee Origins by Country - Kissaten</title>
	<meta name="description" content="Explore coffee beans by their country of origin" />
</svelte:head>

<div class="mx-auto px-4 py-8 container">
	<!-- Header -->
	<div class="mb-12 text-center">
		<h1 class="mb-4 font-bold text-4xl">Coffee Origins</h1>
		<p class="mx-auto max-w-2xl text-muted-foreground text-xl">
			Discover coffee beans from different countries and regions around the world, each with their unique terroir and flavor profiles.
		</p>
	</div>

	<!-- Search Bar -->
	<div class="mx-auto mb-8 max-w-md">
		<div class="relative">
			<Search class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
			<Input
				bind:value={searchQuery}
				placeholder="Search countries..."
				class="pl-10"
			/>
		</div>
	</div>

	<!-- Loading State -->
	{#if loading}
		<div class="py-12 text-center">
			<div class="inline-block border-primary border-b-2 rounded-full w-8 h-8 animate-spin"></div>
			<p class="mt-4 text-muted-foreground">Loading countries...</p>
		</div>
	{/if}

	<!-- Error State -->
	{#if error}
		<div class="py-12 text-center">
			<p class="mb-4 text-red-500">{error}</p>
			<Button onclick={() => window.location.reload()}>Try Again</Button>
		</div>
	{/if}

	<!-- Countries Grid -->
	{#if !loading && !error && filteredCountries}
		<div class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 mb-8">
			{#each filteredCountries as country (country.country_code)}
				<Card class="hover:shadow-lg transition-shadow cursor-pointer" onclick={() => viewCountryBeans(country.country_code)}>
					<CardHeader>
						<CardTitle class="flex items-center space-x-2">
							<span class="text-2xl">{getCountryFlag(country.country_code)}</span>
							<span>{country.country_name}</span>
						</CardTitle>
						<CardDescription class="flex items-center">
							<Globe class="mr-1 w-4 h-4" />
							{country.country_code}
						</CardDescription>
					</CardHeader>
					<CardContent>
						<div class="space-y-3">
							<div class="flex justify-between items-center text-sm">
								<span class="text-muted-foreground">Coffee Beans:</span>
								<span class="flex items-center font-medium">
									<Coffee class="mr-1 w-4 h-4" />
									{country.bean_count}
								</span>
							</div>

							<div class="flex justify-between items-center text-sm">
								<span class="text-muted-foreground">Roasters:</span>
								<span class="font-medium">{country.roaster_count}</span>
							</div>

							<div class="pt-2">
								<Button
									class="w-full"
									variant="outline"
									onclick={(e: MouseEvent) => {
										e.stopPropagation();
										viewCountryBeans(country.country_code);
									}}
								>
									<MapPin class="mr-2 w-4 h-4" />
									Explore Beans
								</Button>
							</div>
						</div>
					</CardContent>
				</Card>
			{/each}
		</div>

		<!-- Results Summary -->
		<div class="text-muted-foreground text-center">
			Showing {filteredCountries.length} of {countries.length} countries
		</div>
	{/if}

	<!-- Empty State -->
	{#if !loading && !error && filteredCountries && filteredCountries.length === 0 && searchQuery}
		<div class="py-12 text-center">
			<Globe class="mx-auto mb-4 w-12 h-12 text-muted-foreground" />
			<h3 class="mb-2 font-semibold text-xl">No countries found</h3>
			<p class="mb-4 text-muted-foreground">Try searching with different keywords.</p>
			<Button onclick={() => searchQuery = ''}>Clear Search</Button>
		</div>
	{/if}
</div>
