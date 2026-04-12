<script lang="ts">
	import { onMount } from "svelte";
	import { getTastingHistory, deleteTasting, type TastingSession } from "$lib/db/localdb";
	import { TASTING_CONVERSATION, DEFECT_CONVERSATION } from "$lib/tasting/conversation";
	import TastingSummaryCard from "$lib/components/tasting/TastingSummaryCard.svelte";
	import { Button } from "$lib/components/ui/button";
	import { Card } from "$lib/components/ui/card";
	import { cn, getFlavourCategoryColors } from "$lib/utils";
	import { Trash2, Search, Calendar, ChevronLeft } from "lucide-svelte";
	import { fade } from "svelte/transition";

	let history = $state<TastingSession[]>([]);
	let isLoading = $state(true);

	onMount(async () => {
		history = await getTastingHistory();
		isLoading = false;
	});

	async function remove(id: number | undefined) {
		if (id === undefined) return;
		if (confirm("Are you sure you want to delete this session?")) {
			await deleteTasting(id);
			history = history.filter(t => t.id !== id);
		}
	}

	function getSearchUrl(notes: string[]) {
		const notesPart = notes.map(n => `"${n}"`).join("&");
		return `/search?tasting_notes_query=${encodeURIComponent(notesPart)}`;
	}

	function getCategoryForNote(note: string) {
		return [...TASTING_CONVERSATION, ...DEFECT_CONVERSATION].find(c =>
			c.flavors?.some(f => (typeof f === 'string' ? f : f.name) === note) ||
			c.subTypes?.some(s => s.flavors.some(f => (typeof f === 'string' ? f : f.name) === note))
		);
	}
</script>

<svelte:head>
	<title>Tasting History | Kissaten</title>
</svelte:head>

<div class="mx-auto mb-24 px-4 py-12 max-w-4xl container">
	<div class="flex justify-between items-center mb-12">
		<div class="flex flex-col gap-2">
			<a href="/tasting" class="flex items-center gap-1 text-muted-foreground hover:text-primary text-sm transition-colors">
				<ChevronLeft size={14} /> Back to Wizard
			</a>
			<h1 class="font-black text-4xl tracking-tighter">Tasting History</h1>
		</div>
		<div class="flex items-center gap-2 bg-primary/10 px-4 py-2 border border-primary/20 rounded-full font-bold text-primary text-sm">
			<Calendar size={16} /> {history.length} Sessions
		</div>
	</div>

	{#if isLoading}
		<div class="space-y-6">
			{#each Array(3) as _}
				<div class="bg-muted rounded-2xl w-full h-48 animate-pulse"></div>
			{/each}
		</div>
	{:else if history.length === 0}
		<Card class="flex flex-col items-center gap-6 p-12 border-dashed text-center">
			<div class="bg-muted p-6 rounded-full">
				<Search size={48} class="text-muted-foreground/30" />
			</div>
			<div class="space-y-2">
				<h2 class="font-bold text-xl">No sessions found</h2>
				<p class="text-muted-foreground">Your guided tasting results will appear here once saved.</p>
			</div>
			<Button href="/tasting">Start a New Tasting</Button>
		</Card>
	{:else}
		<div class="gap-8 grid">
			{#each history as session (session.id)}
				<div transition:fade>
					<Card class="group hover:shadow-xl border-2 overflow-hidden transition-all duration-300">
						<div class="p-6 sm:p-8">
							<div class="flex justify-between items-start mb-6">
								<div class="space-y-1">
									<h3 class="font-black text-2xl tracking-tighter">
										{session.name ? session.name : "Tasting Session"}
									</h3>
									<p class="font-black text-muted-foreground text-xs uppercase tracking-[0.2em]">
										{new Intl.DateTimeFormat('en-GB', { dateStyle: 'full', timeStyle: 'short' }).format(session.date)}
									</p>
								</div>
								<Button variant="ghost" size="icon" class="text-muted-foreground hover:text-destructive shrink-0" onclick={() => remove(session.id)}>
									<Trash2 size={18} />
								</Button>
							</div>

							<div class="gap-6 grid">
								<TastingSummaryCard
									readonly
									class="p-0 border-none shadow-none max-w-none"
									allSelectedNotesList={session.selectedNotes}
									basics={session.basics || {}}
									mouthfeel={session.mouthfeel || {}}
									brewingNotes={session.brewingNotes}
								/>
							</div>

							<div class="flex justify-end mt-4">
								<Button size="sm" variant="outline" class="gap-2" href={getSearchUrl(session.selectedNotes)}>
									<Search size={14} /> Find matching beans
								</Button>
							</div>
						</div>
					</Card>
				</div>
			{/each}
		</div>
	{/if}
</div>
