<script lang="ts">
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "$lib/components/ui/card";
	import type { Roaster } from '$lib/api';
	import 'iconify-icon';
	import { goto } from "$app/navigation";

	interface Props {
		roaster: Roaster;
		class?: string;
	}

	let { roaster, class: className = "" }: Props = $props();

	function handleClick() {
		goto(`/search?roaster=${encodeURIComponent(roaster.name)}`);
	}

	function openWebsite(event: Event) {
		event.stopPropagation();
		if (roaster.website) {
			window.open(roaster.website, '_blank');
		}
	}

	function handleImageError(event: Event) {
		const img = event.currentTarget as HTMLImageElement;
		img.style.display = 'none';
	}

	// Helper to get relative time
	const lastUpdateTime = $derived.by(() => {
		if (!roaster.last_scraped) return '';
		const date = new Date(roaster.last_scraped);
		const now = new Date();
		const diffInDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

		if (diffInDays === 0) return 'Today';
		if (diffInDays === 1) return '1 day ago';
		if (diffInDays < 7) return `${diffInDays} days ago`;
		if (diffInDays < 30) return `${Math.floor(diffInDays / 7)} weeks ago`;
		return date.toLocaleDateString();
	});

</script>

<Card class={`hover:shadow-lg transition-shadow cursor-pointer ${className}`} onclick={handleClick}>
	<CardHeader class="p-0">
		<!-- Logo Header Section -->
		<div class="flex justify-center items-center bg-gray-50 p-4 rounded-t-lg w-full h-32">
			<img
				src="/static/data/roasters/{roaster.slug}/logo.png"
				alt="{roaster.name} Logo"
				class="max-w-full max-h-full object-contain"
				onerror={handleImageError}
			/>
		</div>

		<div class="p-4 pb-2">
			<CardTitle class="mb-1 font-semibold text-gray-900 text-base line-clamp-2">
				{roaster.name}
			</CardTitle>

			{#if roaster.location}
				<CardDescription class="flex items-center text-gray-600 text-xs">
					<iconify-icon icon="mdi:map-marker" width="12" height="12" class="mr-1"></iconify-icon>
					{roaster.location}
				</CardDescription>
			{/if}
		</div>
	</CardHeader>

	<CardContent class="p-4 pt-0">
		<!-- Website Link -->
		{#if roaster.website}
			<div class="mb-2">
				<button
					onclick={openWebsite}
					class="inline-flex items-center font-medium text-amber-600 hover:text-amber-700 text-xs transition-colors"
				>
					<iconify-icon icon="mdi:web" width="12" height="12" class="mr-1"></iconify-icon>
					Visit Website
				</button>
			</div>
		{/if}

		<!-- Bean Count and Last Update -->
		<div class="flex justify-between items-center">
			<div class="font-bold text-gray-900 text-base">
				{roaster.current_beans_count} beans
			</div>
			<div class="text-gray-500 text-xs">
				{lastUpdateTime}
			</div>
		</div>
	</CardContent>
</Card>
