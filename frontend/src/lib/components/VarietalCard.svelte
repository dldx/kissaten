<script lang="ts">
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle,
	} from "$lib/components/ui/card";
	import { Button } from "$lib/components/ui/button/index.js";
	import type { Varietal } from "$lib/api";
	import "iconify-icon";
	import LeafIcon from "~icons/mdi/leaf";

	interface Props {
		varietal: Varietal;
		class?: string;
	}

	let { varietal, class: className = "" }: Props = $props();
</script>

<Card
	class={`flex flex-col hover:shadow-lg transition-shadow varietal-card-shadow varietal-card-dark ${className}`}
>
	<CardHeader class="p-0">
		<!-- Visual Header Section -->
		<div
			class="relative flex justify-center items-center bg-linear-to-br from-green-500 to-green-600 rounded-t-lg w-full h-24 sm:h-32 overflow-hidden"
		>
			<!-- Decorative coffee plant pattern -->
			<div class="absolute inset-0 opacity-20">
				<svg
					class="w-full h-full"
					viewBox="0 0 100 100"
					xmlns="http://www.w3.org/2000/svg"
				>
					<pattern
						id="coffee-pattern-{varietal.slug}"
						x="0"
						y="0"
						width="20"
						height="20"
						patternUnits="userSpaceOnUse"
					>
						<circle cx="10" cy="10" r="2" fill="white" />
						<circle cx="5" cy="15" r="1.5" fill="white" />
						<circle cx="15" cy="5" r="1.5" fill="white" />
					</pattern>
					<rect
						width="100"
						height="100"
						fill="url(#coffee-pattern-{varietal.slug})"
					/>
				</svg>
			</div>

			<!-- Coffee plant icon -->
			<div class="z-10 relative text-white">
				<LeafIcon class="w-8 h-8 sm:w-12 sm:h-12"></LeafIcon>
			</div>
		</div>

		<div class="p-3 sm:p-4 pb-2">
			<div
				class="varietal-card-title-shadow mb-0.5 font-semibold text-gray-900 text-sm sm:text-base line-clamp-1 varietal-card-title-dark"
			>
				{varietal.name}
			</div>

			<CardDescription
				class="text-gray-600 text-[10px] sm:text-xs varietal-card-description-dark"
			>
				Coffee Varietal
			</CardDescription>
		</div>
	</CardHeader>

	<CardContent class="flex flex-col flex-1 p-3 sm:p-4 pt-0">
		<div class="flex-1">
			<!-- Countries with flags -->
			{#if varietal.countries && varietal.countries.length > 0}
				<div class="mb-2">
					<div
						class="varietal-card-label-shadow mb-1 font-medium text-gray-700 text-[10px] sm:text-xs varietal-card-content-dark"
					>
						Grown in:
					</div>
					<div class="flex flex-wrap gap-1">
						{#each varietal.countries.slice(0, 4) as country}
							<div
								class="flex items-center gap-1 bg-gray-100/80 varietal-card-country-shadow px-1.5 py-0.5 rounded text-[10px] sm:text-xs varietal-card-country-dark"
							>
								<iconify-icon
									icon="circle-flags:{country.country_code.toLowerCase()}"
									width="10"
									height="10"
									title={country.country_name}
									class="rounded-sm"
								></iconify-icon>
								<span
									class="text-gray-700 varietal-card-content-dark"
								>
									{country.country_name}
								</span>
							</div>
						{/each}
						{#if varietal.countries.length > 4}
							<span
								class="inline-block bg-gray-100/80 varietal-card-country-shadow px-1.5 py-0.5 rounded text-gray-700 text-[10px] sm:text-xs varietal-card-content-dark varietal-card-country-dark"
							>
								+{varietal.countries.length - 4} more
							</span>
						{/if}
					</div>
				</div>
			{/if}
		</div>

		<!-- Explore Beans Button -->
		<div class="flex flex-row gap-2 mt-auto">
			<Button
				class="flex-1 sm:w-full h-8 sm:h-10 text-xs sm:text-sm px-2 sm:px-4"
				variant="secondary"
				href={`/varietals/${varietal.slug}`}
			>
				<LeafIcon class="mr-1 sm:mr-2 w-3 h-3 sm:w-4 sm:h-4"></LeafIcon>
				Learn
			</Button>
			<Button
				class="flex-1 sm:w-full h-8 sm:h-10 text-xs sm:text-sm px-2 sm:px-4"
				variant="outline"
				href={`/search?variety="${encodeURIComponent(varietal.name)}"`}
			>
				<span class="hidden sm:inline">Explore&nbsp;</span>
				{varietal.bean_count.toLocaleString()} Bean{varietal.bean_count ===
				1
					? ""
					: "s"}
			</Button>
		</div>
	</CardContent>
</Card>
