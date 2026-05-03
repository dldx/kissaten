<script lang="ts">
	import { Droplets, Grape } from "lucide-svelte";
	import { Button } from "$lib/components/ui/button/index.js";
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle,
	} from "$lib/components/ui/card/index.js";
	import type { TastingSession } from "$lib/db/localdb";
	import { getFlavourCategoryColors } from "$lib/utils";
	import { slide } from "svelte/transition";
	import { flip } from "svelte/animate";

	let {
		beanUrlPath,
		tastings = [],
		roasterNotes = [],
		isSaved = false,
	}: {
		beanUrlPath: string;
		tastings: TastingSession[];
		roasterNotes?: any[];
		isSaved?: boolean;
	} = $props();

	let expandedSessions = $state<Record<number, boolean>>({});

	function toggleExpand(id: number) {
		expandedSessions[id] = !expandedSessions[id];
	}

	function getHistoryUrl(session: TastingSession) {
		if (session.beanUrlPath) {
			return `/tasting/history${session.beanUrlPath}/${session.id}`;
		}
		return `/tasting/history/unknown/unknown/${session.id}`;
	}
</script>

<Card
	class="dark:bg-linear-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] mb-4 dark:border-cyan-500/30"
>
	<CardHeader class="pb-3">
		<CardTitle class="flex justify-between items-center text-lg">
			<div class="flex items-center gap-2">
				<Grape class="w-4 h-4 text-emerald-500" />
				<span>Tasting Notes</span>
			</div>
		</CardTitle>
	</CardHeader>
	<CardContent class="space-y-6">
		<!-- Roaster Tasting Notes -->
		{#if roasterNotes.length > 0}
			<div class="space-y-2">
				<div class="flex flex-wrap gap-2">
					{#each roasterNotes as note, note_index (typeof note === "string" ? note : note.note)}
						{@const noteText = typeof note === "string" ? note : note.note}
						{@const flavourCategoryColors = getFlavourCategoryColors(
							typeof note === "string" ? "" : (note.primary_category ?? "")
						)}
						<div animate:flip={{ duration: 400 }} style="display: contents;">
							<a
								class="inline-flex items-center {flavourCategoryColors.bg} {flavourCategoryColors.darkBg} {flavourCategoryColors.text} {flavourCategoryColors.darkText} hover:brightness-95 dark:hover:brightness-125 dark:shadow-[0_0_6px_rgba(34,211,238,0.2)] dark:hover:shadow-[0_0_10px_rgba(34,211,238,0.3)] dark:drop-shadow-[0_0_2px_rgba(34,211,238,0.6)] dark:hover:drop-shadow-[0_0_4px_rgba(34,211,238,0.8)] px-3 py-1 dark:border dark:border-cyan-500/30 dark:hover:border-cyan-400/50 rounded-full font-medium text-sm transition-all duration-200"
								href={`/search?tasting_notes_query="${encodeURIComponent(noteText)}"`}
								title={`Find other coffees with "${noteText}" tasting notes`}
								transition:slide={{ delay: 50 * note_index, duration: 400 }}
							>
								{noteText}
							</a>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- User History Section -->
		{#if tastings.length > 0}
			<div class="space-y-3">
				<h4 class="flex items-center gap-2 font-semibold text-muted-foreground text-xs uppercase tracking-wider">
					Mine
				</h4>
				<div class="space-y-3">
					{#each tastings.slice(0, 3) as session}
						<div class="bg-muted/50 p-2 rounded-lg text-sm">
							<div class="flex justify-between items-center mb-1">
								<a
									href={getHistoryUrl(session)}
									class="opacity-70 font-medium text-xs hover:underline"
								>
									{new Date(session.date).toLocaleDateString(undefined, {
										month: "short",
										day: "numeric",
									})}
								</a>
								{#if session.name}
									<a
										href={getHistoryUrl(session)}
										class="font-bold text-[10px] hover:underline uppercase tracking-wider"
										>{session.name}</a
									>
								{/if}
							</div>
							<div class="flex flex-wrap gap-1">
								{#each expandedSessions[session.id!] ? session.selectedNotes : session.selectedNotes.slice(0, 6) as note}
									<span
										class="inline-flex items-center bg-background/80 dark:shadow-[0_0_6px_rgba(34,211,238,0.2)] px-2 py-0.5 border rounded-full text-xs transition-all duration-200"
										style="border-color: rgba(34, 211, 238, 0.2); border-width: 1px;"
									>
										{note}
									</span>
								{/each}
								{#if session.selectedNotes.length > 6}
									<button
										class="ml-1 text-[10px] text-muted-foreground hover:underline"
										onclick={() => session.id !== undefined && toggleExpand(session.id)}
									>
										{expandedSessions[session.id!] ? "show less" : `+${session.selectedNotes.length - 6}`}
									</button>
								{/if}
							</div>
						</div>
					{/each}
					{#if tastings.length > 3}
						<Button
							variant="link"
							size="sm"
							class="px-0 w-full text-xs"
							href={`/tasting/history${beanUrlPath}`}
						>
							View all {tastings.length} sessions
						</Button>
					{/if}
				</div>

				{#if isSaved || tastings.length > 0}
					<Button
						class="mt-2 w-full"
						variant="outline"
						href="/tasting?bean={encodeURIComponent(beanUrlPath)}"
					>
						<Droplets class="mr-2 w-4 h-4" />
						New Guided Tasting
					</Button>
				{/if}
			</div>
		{:else if isSaved}
			<div class="pt-2">
				<Button
					class="w-full"
					variant="secondary"
					href="/tasting?bean={encodeURIComponent(beanUrlPath)}"
				>
					<Droplets class="mr-2 w-4 h-4" />
					Start Guided Tasting
				</Button>
			</div>
		{/if}
	</CardContent>
</Card>
