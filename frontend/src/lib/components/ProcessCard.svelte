<script lang="ts">
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "$lib/components/ui/card";
	import { Button } from "$lib/components/ui/button/index.js";
	import type { Process } from '$lib/api';
	import 'iconify-icon';
	import { goto } from "$app/navigation";

	interface Props {
		process: Process;
		class?: string;
	}

	let { process, class: className = "" }: Props = $props();

	// Get process category for theming
	const category = $derived(process.category || 'other');

	// Process category colors and icons (visual theming only)
	const categoryConfig = $derived((() => {
		const configs: Record<string, { gradient: string; icon: string }> = {
			washed: {
				gradient: 'from-blue-500 to-blue-600',
				icon: 'mdi:water'
			},
			natural: {
				gradient: 'from-orange-500 to-orange-600',
				icon: 'mdi:white-balance-sunny'
			},
			anaerobic: {
				gradient: 'from-purple-500 to-purple-600',
				icon: 'mdi:flask'
			},
			honey: {
				gradient: 'from-yellow-500 to-yellow-600',
				icon: 'mdi:hexagon'
			},
			fermentation: {
				gradient: 'from-indigo-500 to-indigo-600',
				icon: 'mdi:bacteria'
			},
			experimental: {
				gradient: 'from-pink-500 to-pink-600',
				icon: 'mdi:test-tube'
			},
			decaf: {
				gradient: 'from-red-500 to-red-600',
				icon: 'mdi:coffee-off'
			},
			other: {
				gradient: 'from-gray-500 to-gray-600',
				icon: 'mdi:cog'
			}
		};
		return configs[category] || configs.other;
	})());

	// Use actual data from the API (if available in detailed view)
	const topTastingNotes = $derived(
		(process as any).common_tasting_notes
			? (process as any).common_tasting_notes.slice(0, 4).map((note: any) => note.note)
			: []
	);

	const topCountries = $derived(
		(process as any).top_countries
			? (process as any).top_countries.slice(0, 3).map((country: any) => country.country_name)
			: []
	);
</script>

<Card class={`flex flex-col hover:shadow-lg transition-shadow process-card-shadow process-card-dark ${className}`}>
	<CardHeader class="p-0">
		<!-- Visual Header Section -->
		<div class="relative flex justify-center items-center bg-gradient-to-br {categoryConfig.gradient} rounded-t-lg w-full h-32 overflow-hidden">
			<!-- Decorative pattern -->
			<div class="absolute inset-0 opacity-20">
				<svg class="w-full h-full" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
					<pattern id="process-pattern-{process.slug}" x="0" y="0" width="15" height="15" patternUnits="userSpaceOnUse">
						<circle cx="7.5" cy="7.5" r="1" fill="white"/>
						<circle cx="3" cy="3" r="0.5" fill="white"/>
						<circle cx="12" cy="12" r="0.5" fill="white"/>
						<circle cx="3" cy="12" r="0.5" fill="white"/>
						<circle cx="12" cy="3" r="0.5" fill="white"/>
					</pattern>
					<rect width="100" height="100" fill="url(#process-pattern-{process.slug})"/>
				</svg>
			</div>

			<!-- Process icon -->
			<div class="z-10 relative text-white">
				<iconify-icon icon={categoryConfig.icon} width="48" height="48"></iconify-icon>
			</div>
		</div>

		<div class="p-4 pb-2">
			<CardTitle class="process-card-title-shadow mb-1 font-semibold text-gray-900 text-base line-clamp-2 process-card-title-dark">
				{process.name}
			</CardTitle>

			<CardDescription class="text-gray-600 text-xs process-card-description-dark">
				Processing Method
			</CardDescription>
		</div>
	</CardHeader>

	<CardContent class="flex flex-col flex-1 p-4 pt-0">
		<div class="flex-1">
			<!-- Top Countries -->
			{#if topCountries.length > 0}
				<div class="mb-2">
					<div class="process-card-label-shadow mb-1 font-medium text-gray-700 text-xs process-card-content-dark">Popular Origins</div>
					<div class="font-medium text-gray-600 text-xs process-card-content-dark process-card-content-shadow">
						{topCountries.join(' • ')}
					</div>
				</div>
			{/if}

			<!-- Common Tasting Notes -->
			{#if topTastingNotes.length > 0}
				<div class="mb-2">
					<div class="process-card-label-shadow mb-1 font-medium text-gray-700 text-xs process-card-content-dark">Common Flavors</div>
					<div class="flex flex-wrap gap-1">
						{#each topTastingNotes as note}
							<span class="inline-block bg-blue-100 process-card-note-shadow px-1.5 py-0.5 rounded font-medium text-blue-800 text-xs process-card-note-dark">
								{note}
							</span>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Countries Summary -->
			{#if process.country_count > 0}
				<div class="mb-2">
					<div class="font-medium text-gray-700 text-xs process-card-content-dark process-card-content-shadow">
						Used in {process.country_count} countries
					</div>
				</div>
			{/if}

		</div>

		<!-- Explore Beans Button -->
		<div class="flex flex-row gap-2 mt-auto">
			<Button
				class="w-full"
				variant="secondary"
				href={`/process/${process.slug}`}
			>
				<iconify-icon icon={categoryConfig.icon} class="mr-2" width="16" height="16"></iconify-icon>
				Learn
			</Button>
			<Button
				class="w-full"
				variant="outline"
				href={`/search?process="${encodeURIComponent(process.name)}"`}
			>
				Explore {process.bean_count.toLocaleString()} Bean{process.bean_count === 1 ? '' : 's'}
			</Button>
		</div>
	</CardContent>
</Card>


