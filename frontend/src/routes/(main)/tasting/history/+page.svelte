<script lang="ts">
	import {
		getTastingHistory,
		type TastingSession,
	} from "$lib/db/localdb";
	import { dbUpdateTrigger } from "$lib/db/updates.svelte";
	import { Button } from "$lib/components/ui/button";
	import { Calendar, Plus } from "lucide-svelte";
	import SearchBar from "$lib/components/search/SearchBar.svelte";
	import TastingSessionList from "$lib/components/tasting/TastingSessionList.svelte";
	import { searchTastingHistory } from "$lib/utils/search";

	let { data } = $props();

	let tastingHistory = $state<TastingSession[]>(data.history || []);
	let isLoading = $state(tastingHistory.length === 0);
	let searchQuery = $state("");

	const filteredHistory = $derived(
		searchTastingHistory(tastingHistory, searchQuery),
	);

	const isSearching = $derived(searchQuery.trim().length > 0);

	$effect(() => {
		const trigger = dbUpdateTrigger.tastingHistory;
		getTastingHistory().then((history) => {
			tastingHistory = history;
			isLoading = false;
			console.log(`[TastingHistory] Loaded ${history.length} sessions`);
		});
	});
</script>

<svelte:head>
	<title>Tasting History | Kissaten</title>
	<meta
		name="description"
		content="Review your past coffee tasting sessions and notes."
	/>
	<meta name="robots" content="noindex,follow" />
	<link rel="canonical" href="https://kissaten.app/tasting/history" />
</svelte:head>

<div class="mb-24">
	<div class="flex flex-col sm:flex-row sm:items-center gap-4 sm:justify-between mb-8">
		<div class="flex w-full items-center justify-between gap-3 sm:w-auto sm:justify-start">
			<p class="flex items-center gap-1.5 text-muted-foreground text-sm">
				<Calendar size={15} />
				{#if isSearching}
					{filteredHistory.length} of {tastingHistory.length} sessions
				{:else}
					{tastingHistory.length} session{tastingHistory.length !== 1 ? "s" : ""}
				{/if}
			</p>

			<Button href="/tasting" size="sm" class="gap-2 shadow-sm px-4 rounded-full h-10">
				<Plus size={16} /> New Tasting
			</Button>
		</div>

		<div class="w-full sm:max-w-xs">
			<SearchBar
				bind:value={searchQuery}
				placeholder="Find a session..."
				showButton={false}
			/>
		</div>
	</div>

	{#if isLoading}
		<div class="space-y-3" aria-busy="true">
			{#each Array(6) as _}
				<div class="bg-muted rounded-xl w-full h-20 animate-pulse"></div>
			{/each}
		</div>
	{:else}
		<TastingSessionList
			sessions={filteredHistory}
			searchActive={isSearching}
			{searchQuery}
			onClearSearch={() => (searchQuery = "")}
		>
		</TastingSessionList>
	{/if}
</div>
