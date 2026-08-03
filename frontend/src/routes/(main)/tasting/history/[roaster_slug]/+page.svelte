<script lang="ts">
	import { page } from "$app/state";
	import { getTastingHistory, type TastingSession } from "$lib/db/localdb";
	import { dbUpdateTrigger } from "$lib/db/updates.svelte";
	import { Button } from "$lib/components/ui/button";
	import TastingSessionList from "$lib/components/tasting/TastingSessionList.svelte";
	import { Calendar, Plus } from "lucide-svelte";
	import { KissatenAPI } from "$lib/api";

	const roasterSlug = $derived(page.params.roaster_slug || "");
	const api = new KissatenAPI();

	let tastingHistory = $state<TastingSession[]>([]);
	let isLoading = $state(true);
	let roasterName = $state<string>("");

	const filteredTastings = $derived(
		tastingHistory.filter((t) => {
			if (!t.beanUrlPath) return false;
			const parts = t.beanUrlPath.split("/").filter(Boolean);
			return parts[0] === roasterSlug;
		}),
	);

	$effect(() => {
		const trigger = dbUpdateTrigger.tastingHistory;
		void refresh();
	});

	async function refresh() {
		try {
			const [history, response] = await Promise.all([
				getTastingHistory(),
				api.getRoasters(),
			]);
			tastingHistory = history;

			const roasters = response.data || [];
			const roaster = roasters.find((r) => r.slug === roasterSlug);
			if (roaster) {
				roasterName = roaster.name;
			} else {
				roasterName = roasterSlug
					.split(/[_-]+/)
					.map((w) => w.charAt(0).toUpperCase() + w.slice(1))
					.join(" ");
			}
		} catch (error) {
			console.error("Failed to load tasting history or roasters:", error);
		} finally {
			isLoading = false;
		}
	}
</script>

<svelte:head>
	<title>{roasterName} Tasting History | Kissaten</title>
	<meta
		name="description"
		content="View all coffee tasting sessions for {roasterName}."
	/>
	<meta name="robots" content="noindex,follow" />
</svelte:head>

<div class="mb-24">
	<div class="flex flex-col sm:flex-row sm:items-center gap-4 sm:justify-between mb-8">
		<p class="flex items-center gap-1.5 text-muted-foreground text-sm">
			<Calendar size={15} />
			{filteredTastings.length} session{filteredTastings.length !== 1 ? "s" : ""}
		</p>

		<Button href="/tasting" size="sm" class="gap-2 shadow-sm px-4 rounded-full h-10">
			<Plus size={16} /> New Tasting
		</Button>
	</div>

	{#if isLoading}
		<div class="space-y-3" aria-busy="true">
			{#each Array(6) as _}
				<div class="bg-muted rounded-xl w-full h-20 animate-pulse"></div>
			{/each}
		</div>
	{:else}
		<TastingSessionList
			sessions={filteredTastings}
			emptyTitle="No sessions found"
			emptyDescription={`You haven't recorded any tastings for ${roasterName} yet.`}
		/>
	{/if}
</div>
