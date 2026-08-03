<script lang="ts">
	import type { TastingSession } from "$lib/db/localdb";
	import { groupSessionsByMonth } from "$lib/utils/history";
	import { deleteTasting } from "$lib/utils/tasting_utils";
	import TastingSessionListItem from "./TastingSessionListItem.svelte";
	import { Card } from "$lib/components/ui/card";
	import { Button } from "$lib/components/ui/button";
	import { Coffee, Search, Plus } from "lucide-svelte";

	interface Props {
		sessions: TastingSession[];
		searchActive?: boolean;
		searchQuery?: string;
		emptyTitle?: string;
		emptyDescription?: string;
		onClearSearch?: () => void;
	}

	const PAGE_SIZE = 12;

	let { sessions, searchActive = false, searchQuery = "", emptyTitle, emptyDescription, onClearSearch }: Props =
		$props();

	let visibleCount = $state(PAGE_SIZE);

	const hasMore = $derived(sessions.length > visibleCount);
	const visible = $derived(sessions.slice(0, visibleCount));
	const groups = $derived(searchActive ? null : groupSessionsByMonth(visible));

	const showEndCap = $derived(
		!hasMore && !searchActive && sessions.length >= 6,
	);

	async function handleDelete(session: TastingSession) {
		// deleteTasting notifies the tastingHistory db trigger, which the
		// parent list page listens to and refetches from — no local state needed.
		await deleteTasting(session.id);
	}
</script>

{#if sessions.length === 0}
	<Card class="flex flex-col items-center gap-6 p-12 border-dashed text-center">
		<div class="bg-muted p-6 rounded-full">
			{#if searchActive}
				<Search size={48} class="text-muted-foreground/30" />
			{:else}
				<Coffee size={48} class="text-muted-foreground/30" />
			{/if}
		</div>
		<div class="space-y-2">
			<h2 class="font-bold text-xl">
				{searchActive ? "No matching sessions" : (emptyTitle || "No sessions found")}
			</h2>
			<p class="text-muted-foreground">
				{searchActive
					? `We couldn't find any results for "${searchQuery}"`
					: (emptyDescription || "Your guided tasting results will appear here once saved.")}
			</p>
		</div>
		{#if searchActive}
			<Button
				variant="outline"
				onclick={() => onClearSearch?.()}
			>
				Clear Search
			</Button>
		{:else}
			<Button href="/tasting">
				<Plus /> New Guided Tasting
			</Button>
		{/if}
	</Card>
{:else}
	<div class="space-y-8">
		{#if groups}
			{#each groups as group}
				<section class="space-y-3">
					<div class="flex items-center gap-3">
						<h2
							class="font-bold text-muted-foreground text-xs uppercase tracking-[0.2em]"
						>
							{group.label}
						</h2>
						<div class="flex-1 border-t border-muted"></div>
					</div>
					<div class="space-y-3">
						{#each group.sessions as session (session.id)}
							<TastingSessionListItem
								{session}
								onDelete={() => handleDelete(session)}
							/>
						{/each}
					</div>
				</section>
			{/each}
		{:else}
			<div class="space-y-3">
				{#each visible as session (session.id)}
					<TastingSessionListItem
						{session}
						onDelete={() => handleDelete(session)}
					/>
				{/each}
			</div>
		{/if}

		{#if hasMore}
			<div class="flex justify-center pt-2">
				<Button
					variant="outline"
					onclick={() => (visibleCount = visibleCount + PAGE_SIZE)}
				>
					Show more ({sessions.length - visibleCount} remaining)
				</Button>
			</div>
		{/if}

		{#if showEndCap}
			<div class="pt-4 text-center">
				<div class="mb-4 flex items-center gap-3">
					<div class="flex-1 border-t border-muted"></div>
					<Coffee size={16} class="text-muted-foreground/40" />
					<div class="flex-1 border-t border-muted"></div>
				</div>
				<p class="mb-3 text-muted-foreground text-sm">
					That's every session — fancy another cup?
				</p>
				<Button variant="outline" href="/tasting">
					<Plus /> New Tasting
				</Button>
			</div>
		{/if}
	</div>
{/if}
