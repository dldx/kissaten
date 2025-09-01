<script lang="ts">
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "$lib/components/ui/card";
	import type { Varietal } from '$lib/api';
	import 'iconify-icon';
	import { goto } from "$app/navigation";

	interface Props {
		varietal: Varietal;
		class?: string;
	}

	let { varietal, class: className = "" }: Props = $props();

	function handleClick() {
		goto(`/varietals/${varietal.slug}`);
	}

</script>

<Card class={`hover:shadow-lg transition-shadow cursor-pointer ${className}`} onclick={handleClick}>
	<CardHeader class="p-0">
		<!-- Visual Header Section -->
		<div class="relative flex justify-center items-center bg-gradient-to-br from-green-500 to-green-600 rounded-t-lg w-full h-32 overflow-hidden">
			<!-- Decorative coffee plant pattern -->
			<div class="absolute inset-0 opacity-20">
				<svg class="w-full h-full" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
					<pattern id="coffee-pattern-{varietal.slug}" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
						<circle cx="10" cy="10" r="2" fill="white"/>
						<circle cx="5" cy="15" r="1.5" fill="white"/>
						<circle cx="15" cy="5" r="1.5" fill="white"/>
					</pattern>
					<rect width="100" height="100" fill="url(#coffee-pattern-{varietal.slug})"/>
				</svg>
			</div>

			<!-- Coffee plant icon -->
			<div class="z-10 relative text-white">
				<iconify-icon icon="mdi:leaf" width="48" height="48"></iconify-icon>
			</div>
		</div>

		<div class="p-4 pb-2">
			<CardTitle class="mb-1 font-semibold text-gray-900 text-base line-clamp-2">
				{varietal.name}
			</CardTitle>

			<CardDescription class="text-gray-600 text-xs">
				Coffee Varietal
			</CardDescription>
		</div>
	</CardHeader>

	<CardContent class="p-4 pt-0">


		<!-- Countries with flags -->
		{#if varietal.countries && varietal.countries.length > 0}
			<div class="mb-2">
				<div class="mb-1 font-medium text-gray-700 text-xs">Countries</div>
				<div class="flex flex-wrap gap-1">
					{#each varietal.countries as country}
						<div class="flex items-center gap-1 bg-gray-100 px-1.5 py-0.5 rounded text-xs">
							<iconify-icon
								icon="circle-flags:{country.country_code.toLowerCase()}"
								width="12"
								height="12"
								title={country.country_name}
								class="rounded-sm"
							></iconify-icon>
							<span class="text-gray-700">{country.country_name}</span>
						</div>
					{/each}
					{#if varietal.countries.length > 6}
						<span class="inline-block bg-gray-100 px-1.5 py-0.5 rounded text-gray-700 text-xs">
							+{varietal.countries.length - 6} more
						</span>
					{/if}
				</div>
			</div>
		{/if}

		<!-- Bean Count -->
		<div class="flex justify-between items-center">
			<div class="font-bold text-gray-900 text-base">
				{varietal.bean_count.toLocaleString()} beans
			</div>
		</div>

	</CardContent>
</Card>


