<script lang="ts">
	import type { GroupedPodcastHit } from "$lib/api";
    import { Lightbulb } from "@lucide/svelte";
	import PodcastInsightCard from "./PodcastInsightCard.svelte";
	import { userSettings } from "$lib/stores/userSettings.svelte";
	interface Props {
		podcasts: GroupedPodcastHit[];
		topic?: string;
		subtitle?: string;
		class?: string;
	}

	let { podcasts, topic, subtitle, class: className }: Props = $props();
</script>

{#if userSettings.betaEnabled && podcasts && podcasts.length > 0}
	<div class={className || "mt-12"}>
		<div class="flex items-center gap-3 mb-6">
			<div
				class="bg-purple-100 dark:bg-purple-900/40 p-2 rounded-lg text-purple-600 dark:text-purple-400"
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
			{#each podcasts as group}
				<PodcastInsightCard {group} />
			{/each}
		</div>
	</div>
{/if}
