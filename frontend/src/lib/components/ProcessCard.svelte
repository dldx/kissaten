<script lang="ts">
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle,
	} from "$lib/components/ui/card";
	import { Button } from "$lib/components/ui/button/index.js";
	import type { Process } from "$lib/api";
	import { getProcessCategory, getProcessCategoryConfig } from "$lib/utils";
	import "iconify-icon";

	interface Props {
		process: Process;
		class?: string;
	}

	let { process, class: className = "" }: Props = $props();

	// Get process category for theming
	const category = $derived(
		process.category || getProcessCategory(process.name),
	);

	// Process category colors and icons (visual theming only)
	const categoryConfig = $derived(getProcessCategoryConfig(category));
</script>

<Card
	class={`flex flex-col hover:shadow-lg transition-shadow process-card-shadow process-card-dark ${className}`}
>
	<CardHeader class="p-0">
		<!-- Visual Header Section -->
		<div
			class="relative flex justify-center items-center bg-gradient-to-br {categoryConfig.gradient} rounded-t-lg w-full h-24 sm:h-32 overflow-hidden"
		>
			<!-- Decorative pattern -->
			<div class="absolute inset-0 opacity-20">
				<svg
					class="w-full h-full"
					viewBox="0 0 100 100"
					xmlns="http://www.w3.org/2000/svg"
				>
					<pattern
						id="process-pattern-{process.slug}"
						x="0"
						y="0"
						width="15"
						height="15"
						patternUnits="userSpaceOnUse"
					>
						<circle cx="7.5" cy="7.5" r="1" fill="white" />
						<circle cx="3" cy="3" r="0.5" fill="white" />
						<circle cx="12" cy="12" r="0.5" fill="white" />
						<circle cx="3" cy="12" r="0.5" fill="white" />
						<circle cx="12" cy="3" r="0.5" fill="white" />
					</pattern>
					<rect
						width="100"
						height="100"
						fill="url(#process-pattern-{process.slug})"
					/>
				</svg>
			</div>

			<!-- Process icon -->
			<div class="z-10 relative text-white">
				<categoryConfig.icon class="w-8 h-8 sm:w-12 sm:h-12" />
			</div>
		</div>

		<div class="p-3 sm:p-4 pb-2">
			<div
				class="process-card-title-shadow mb-0.5 font-semibold text-gray-900 text-sm sm:text-base line-clamp-1 process-card-title-dark"
			>
				{process.name}
			</div>

			<CardDescription
				class="text-gray-600 text-[10px] sm:text-xs process-card-description-dark"
			>
				Processing Method
			</CardDescription>
		</div>
	</CardHeader>

	<CardContent class="flex flex-col flex-1 p-3 sm:p-4 pt-0">
		<div class="flex-1">
			<!-- Countries with flags -->
			{#if process.countries && process.countries.length > 0}
				<div class="mb-2">
					<div
						class="varietal-card-label-shadow mb-1 font-medium text-gray-700 text-[10px] sm:text-xs varietal-card-content-dark"
					>
						Found in:
					</div>
					<div class="flex flex-wrap gap-1">
						{#each process.countries.slice(0, 4) as country}
							<div
								class="flex items-center gap-1 bg-gradient-to-br process-card-country-shadow px-1.5 py-0.5 rounded text-[10px] sm:text-xs process-card-country-dark"
							>
								<iconify-icon
									icon="circle-flags:{country.country_code.toLowerCase()}"
									width="10"
									height="10"
									title={country.country_name}
									class="rounded-sm"
								></iconify-icon>
								<span
									class="text-gray-700 process-card-content-dark"
								>
									{country.country_name}
								</span>
							</div>
						{/each}
						{#if process.countries.length > 4}
							<span
								class="inline-block bg-linear-to-br process-card-country-shadow px-1.5 py-0.5 rounded text-gray-700 text-[10px] sm:text-xs process-card-content-dark process-card-country-dark"
							>
								+{process.countries.length - 4} more
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
				href={`/processes/${process.slug}`}
			>
				<categoryConfig.icon
					class="mr-1 sm:mr-2 w-3 h-3 sm:w-4 sm:h-4"
				/>
				Learn
			</Button>
			<Button
				class="flex-1 sm:w-full h-8 sm:h-10 text-xs sm:text-sm px-2 sm:px-4"
				variant="outline"
				href={`/search?process="${encodeURIComponent(process.name)}"`}
			>
				<span class="hidden sm:inline">Explore&nbsp;</span>
				{process.bean_count.toLocaleString()} Bean{process.bean_count ===
				1
					? ""
					: "s"}
			</Button>
		</div>
	</CardContent>
</Card>
