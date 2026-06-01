<script lang="ts">
	import type { GroupedPodcastHit } from "$lib/api";
	import { Lightbulb, ChevronDown, ChevronUp } from "@lucide/svelte";
	import PodcastInsightCard from "./PodcastInsightCard.svelte";
	import { userSettings } from "$lib/stores/userSettings.svelte";
	import { Button } from "$lib/components/ui/button";

	interface Props {
		podcasts: GroupedPodcastHit[];
		topic?: string;
		subtitle?: string;
		class?: string;
		isLoading?: boolean;
	}

	let {
		podcasts,
		topic,
		subtitle,
		class: className,
		isLoading = false,
	}: Props = $props();

	let expanded = $state(false);
	const visiblePodcasts = $derived(
		expanded ? podcasts : podcasts.slice(0, 3)
	);
	const hasMore = $derived(!isLoading && podcasts.length > 3);
</script>

{#if !isLoading && userSettings.betaEnabled && podcasts && podcasts.length > 0}
	<div class={className || "mt-12"}>
		<div class="flex items-center gap-3 mb-6">
			<div
				class="bg-purple-100 dark:bg-purple-900/40 p-2 rounded-lg text-purple-600 dark:text-purple-400 {isLoading
					? 'animate-pulse'
					: ''}"
			>
				<Lightbulb class="w-6 h-6" />
			</div>
			<div>
				<h2 class="font-bold text-gray-900 dark:text-emerald-300 text-2xl">
					Expert Insights
				</h2>
				{#if subtitle}
					<p class="text-gray-500 dark:text-cyan-400/60 text-sm">
						{subtitle}
					</p>
				{:else if topic}
					<p class="text-gray-500 dark:text-cyan-400/60 text-sm">
						Learn more from coffee experts
					</p>
				{/if}
			</div>
		</div>

		<div class="gap-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
			{#each visiblePodcasts as group}
				<PodcastInsightCard {group} />
			{/each}
		</div>

		{#if hasMore}
			<div class="flex justify-center mt-6">
				<Button
					variant="ghost"
					size="sm"
					class="text-purple-600 hover:text-purple-700 dark:hover:text-purple-300 dark:text-purple-400"
					onclick={() => (expanded = !expanded)}
				>
					{#if expanded}
						Show less
						<ChevronUp class="ml-1.5 w-4 h-4" />
					{:else}
						Show {podcasts.length - 3} more insights
						<ChevronDown class="ml-1.5 w-4 h-4" />
					{/if}
				</Button>
			</div>
		{/if}
	</div>
{/if}
