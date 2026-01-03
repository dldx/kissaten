<script lang="ts">
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle,
	} from "$lib/components/ui/card";
	import { Button } from "$lib/components/ui/button/index.js";
	import { Coffee } from "lucide-svelte";
	import type { Roaster } from "$lib/api";
	import "iconify-icon";
	import MapMarkerIcon from "virtual:icons/mdi/map-marker";
	import WebIcon from "virtual:icons/mdi/web";
	import { addUtmParams } from "$lib/utils";

	interface Props {
		roaster: Roaster;
		class?: string;
	}

	let { roaster, class: className = "" }: Props = $props();

	function handleImageError(event: Event) {
		const img = event.currentTarget as HTMLImageElement;
		img.style.display = "none";
	}

	// Helper to get relative time
	const lastUpdateTime = $derived.by(() => {
		if (!roaster.last_scraped) return "";
		const date = new Date(roaster.last_scraped);
		const now = new Date();
		const diffInDays = Math.floor(
			(now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24),
		);

		if (diffInDays === 0) return "Today";
		if (diffInDays === 1) return "1 day ago";
		if (diffInDays < 7) return `${diffInDays} days ago`;
		if (diffInDays < 30) return `${Math.floor(diffInDays / 7)} weeks ago`;
		return date.toLocaleDateString();
	});
</script>

<Card
	class={`flex flex-col hover:shadow-lg varietal-card-shadow varietal-card-dark transition-shadow dark:bg-slate-800/80 ${className}`}
>
	<CardHeader class="p-0">
		<!-- Logo Header Section -->
		<div
			class="flex justify-center items-center bg-gray-50 dark:bg-slate-400/60 p-4 rounded-t-lg w-full h-32"
		>
			<img
				src="/static/data/roasters/{roaster.slug}/logo.png"
				alt="{roaster.name} Logo"
				class="max-w-full max-h-full object-contain"
				onerror={handleImageError}
			/>
		</div>

		<div class="p-4 pb-2">
			<CardTitle
				class="mb-1 font-semibold text-gray-900 dark:text-cyan-100 text-base line-clamp-2"
			>
				{roaster.name}
			</CardTitle>

			{#if roaster.location}
				<CardDescription
					class="flex items-center text-gray-600 dark:text-cyan-300/80 text-xs"
				>
					<MapMarkerIcon
						width="12"
						height="12"
						class="mr-1 text-gray-500 dark:text-cyan-400"
					></MapMarkerIcon>
					{roaster.location}
				</CardDescription>
			{/if}
		</div>
	</CardHeader>

	<CardContent class="flex flex-col flex-1 p-4 pt-0">
		<div class="flex-1">
			<!-- Website Link -->
			{#if roaster.website}
				<div class="mb-2">
					<a
						href={addUtmParams(roaster.website, {
							source: "kissaten.app",
							medium: "referral",
							campaign: "roaster_profile",
						})}
						target="_blank"
						class="inline-flex items-center font-medium text-amber-600 hover:text-amber-700 dark:hover:text-orange-300 dark:text-orange-400 text-xs transition-colors"
					>
						<WebIcon width="12" height="12" class="mr-1"></WebIcon>
						Visit Website
					</a>
				</div>
			{/if}

			<!-- Bean Count and Last Update -->
			<div class="flex justify-between items-center mb-3">
				<div class="text-gray-500 dark:text-cyan-400/70 text-xs">
					{lastUpdateTime}
				</div>
			</div>
		</div>

		<!-- Explore Beans Button -->
		<div class="mt-auto">
			<Button
				class="w-full"
				variant="outline"
				href={`/search?roaster=${encodeURIComponent(roaster.name)}`}
			>
				<Coffee class="mr-2 w-4 h-4" />
				Explore {roaster.current_beans_count.toLocaleString()} Bean{roaster.current_beans_count ===
				1
					? ""
					: "s"}
			</Button>
		</div>
	</CardContent>
</Card>
