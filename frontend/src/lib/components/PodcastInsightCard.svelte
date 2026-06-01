<script lang="ts">
	import type { GroupedPodcastHit, PodcastSearchHit } from "$lib/api";
	import { Mic, ExternalLink, Clock, FileText, Video } from "lucide-svelte";
	import { Button } from "$lib/components/ui/button";

	interface Props {
		group: GroupedPodcastHit;
	}

	let { group }: Props = $props();

	// If it's an episode recommendation, we might show the primary segment or a condensed list
	const primaryHit = $derived(group.segments[0]);
	const mediaType = $derived(group.media_type ?? "podcast");

	const mediaConfig = $derived.by(() => {
		switch (mediaType) {
			case "blog":
				return {
					icon: FileText,
					label: "Blog Post",
					actionText: "Read Article",
					color: "emerald",
					bgClass: "bg-emerald-100 dark:bg-emerald-900/40",
					textClass: "text-emerald-600 dark:text-emerald-400",
					labelClass: "text-gray-500 dark:text-emerald-300/70",
					borderClass: "dark:border-emerald-500/30",
				};
			case "video":
				return {
					icon: Video,
					label: "Video",
					actionText: "Watch Video",
					color: "red",
					bgClass: "bg-red-100 dark:bg-red-900/40",
					textClass: "text-red-600 dark:text-red-400",
					labelClass: "text-gray-500 dark:text-red-300/70",
					borderClass: "dark:border-red-500/30",
				};
			default:
				return {
					icon: Mic,
					label: "Podcast",
					actionText: "Listen to Episode",
					color: "purple",
					bgClass: "bg-purple-100 dark:bg-purple-900/40",
					textClass: "text-purple-600 dark:text-purple-400",
					labelClass: "text-gray-500 dark:text-purple-300/70",
					borderClass: "dark:border-purple-500/30",
				};
		}
	});

	function formatTimestamp(seconds: number | null): string {
		if (seconds == null) return "";
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins}:${secs.toString().padStart(2, "0")}`;
	}

	function hasTimestamp(hit: PodcastSearchHit): boolean {
		return hit.timestamp_start != null && hit.timestamp_start > 0;
	}

	function getPodcastDisplayName(name: string): string {
		return name
			.split("-")
			.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
			.join(" ");
	}

	function formatDate(dateStr: string | null | undefined): string {
		if (!dateStr) return "";
		try {
			const date = new Date(dateStr);
			return date.toLocaleDateString("en-US", {
				month: "short",
				day: "numeric",
				year: "numeric"
			});
		} catch (e) {
			return dateStr.split(" ").slice(0, 4).join(" ");
		}
	}
</script>

<div
	class="flex flex-col bg-white dark:bg-slate-800/60 shadow-sm hover:shadow-md border border-gray-200 {mediaConfig.borderClass} rounded-xl h-full overflow-hidden transition-all"
>
	<!-- Header -->
	<div class="px-5 pt-5">
		<div class="flex justify-between items-center mb-2">
			<div class="flex items-center gap-2">
				<div
					class="{mediaConfig.bgClass} p-1.5 rounded-lg {mediaConfig.textClass}"
				>
					<mediaConfig.icon class="w-4 h-4" />
				</div>
				<span
					class="font-medium {mediaConfig.labelClass} text-xs uppercase tracking-wider"
				>
					{getPodcastDisplayName(group.podcast_name)}
				</span>
			</div>
			{#if group.published_date}
				<span class="font-medium text-[10px] text-gray-400 dark:text-purple-400/50 uppercase">
					{formatDate(group.published_date)}
				</span>
			{/if}
		</div>
		<h3
			class="font-bold text-gray-900 dark:text-cyan-100 text-lg line-clamp-2 leading-tight"
			title={group.episode_title}
		>
			<a href={group.url} target="_blank" rel="noopener noreferrer">{group.episode_title}</a>
		</h3>
	</div>

	<!-- Content -->
	<div class="flex-1 space-y-4 p-5">
		{#if group.is_episode_recommendation && group.segments.length > 1}
			<div class="space-y-3">
				<p class="text-gray-600 dark:text-cyan-200/80 text-sm">
					This {mediaConfig.label.toLowerCase()} covers multiple related topics.
				</p>
				<div class="space-y-2">
					{#each group.segments.slice(0, 2) as segment}
						<div
							class="bg-gray-50 dark:bg-slate-900/40 p-2 border border-gray-100 dark:border-purple-500/10 rounded"
						>
							<div
								class="flex justify-between items-center mb-1 text-[10px] uppercase"
							>
								<span
									class="font-bold text-purple-600 dark:text-purple-400"
									>{segment.title}</span
								>
								{#if hasTimestamp(segment)}
									<span class="text-gray-400"
										>{formatTimestamp(segment.timestamp_start)}</span
									>
								{/if}
							</div>
							<p
								class="text-gray-500 dark:text-cyan-400/70 text-xs line-clamp-2"
							>
								{segment.summary}
							</p>
						</div>
					{/each}
					{#if group.segments.length > 2}
						<div class="text-gray-400 text-xs text-center italic">
							+ {group.segments.length - 2} more segments
						</div>
					{/if}
				</div>
			</div>
		{:else}
			{#if hasTimestamp(primaryHit)}
				<div
					class="flex items-center gap-2 text-gray-500 dark:text-cyan-400/60 text-sm italic"
				>
					<Clock class="w-4 h-4" />
					<span
						>{formatTimestamp(primaryHit.timestamp_start)} - {formatTimestamp(
							primaryHit.timestamp_end,
						)}</span
					>
				</div>
			{/if}

			<div class="space-y-2">
				<h4
					class="font-semibold text-gray-800 dark:text-emerald-400 text-sm"
				>
					{primaryHit.title}
				</h4>
				<p
					class="text-gray-600 dark:text-cyan-200/80 text-sm line-clamp-6 leading-relaxed"
				>
					{primaryHit.summary}
				</p>
			</div>
		{/if}
	</div>

	<!-- Footer -->
	<div
		class="bg-gray-50/50 dark:bg-slate-900/20 px-5 py-4 border-gray-100 dark:border-purple-500/20 border-t"
	>
		{#if group.url}
			<Button
				variant="outline"
				size="sm"
				class="group w-full text-xs"
				href={group.url}
				target="_blank"
			>
				{mediaConfig.actionText}
				<ExternalLink
					class="ml-2 w-3.5 h-3.5 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
				/>
			</Button>
		{:else}
			<div
				class="text-gray-400 dark:text-cyan-400/30 text-xs text-center italic"
			>
				{mediaType === "podcast" ? "Transcript only" : "No link available"}
			</div>
		{/if}
	</div>
</div>
