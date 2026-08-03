<script lang="ts">
	import { page } from "$app/state";
	import { getTastingHistory, type TastingSession } from "$lib/db/localdb";
	import { dbUpdateTrigger } from "$lib/db/updates.svelte";
	import { Button } from "$lib/components/ui/button";
	import TastingSessionList from "$lib/components/tasting/TastingSessionList.svelte";
	import { Calendar, Plus, Coffee } from "lucide-svelte";
	import { KissatenAPI } from "$lib/api";
	import { slugifyCustomRoaster, getCustomRoasterName } from "$lib/utils/tasting_utils";

	const roasterSlug = $derived(page.params.roaster_slug || "");
	const isCustomHub = $derived(roasterSlug === "custom");
	const api = new KissatenAPI();

	let tastingHistory = $state<TastingSession[]>([]);
	let isLoading = $state(true);
	let roasterName = $state<string>("Custom Beans");

	const filteredTastings = $derived(
		tastingHistory.filter((t) => {
			if (!t.beanUrlPath) return false;
			const parts = t.beanUrlPath.split("/").filter(Boolean);
			return parts[0] === roasterSlug;
		}),
	);

	// Distinct custom roasters (by slug) among the custom sessions, plus a
	// readable label and count for each. Used to render the custom-roaster chips.
	const customRoasters = $derived(
		Array.from(
			[...filteredTastings]
				.reduce((map, t) => {
					const name = getCustomRoasterName(t);
					const slug = slugifyCustomRoaster(name);
					if (!slug) return map;
					if (!map.has(slug)) {
						map.set(slug, { slug, name: name || "Unknown Roaster", count: 0 });
					}
					const entry = map.get(slug)!;
					entry.count += 1;
					return map;
				}, new Map<string, { slug: string; name: string; count: number }>())
				.values(),
		),
	);

	$effect(() => {
		const trigger = dbUpdateTrigger.tastingHistory;
		void refresh();
	});

	async function refresh() {
		try {
			let history = await getTastingHistory();

			if (isCustomHub) {
				// Custom hub: no real roaster to look up, just use all custom sessions.
				tastingHistory = history;
				roasterName = "Custom Beans";
			} else {
				const response = await api.getRoasters();
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
	{:else if isCustomHub && customRoasters.length > 0}
		<div class="flex flex-wrap gap-2 mb-6">
			{#each customRoasters as cr}
				<a
					href={`/tasting/history/custom/${cr.slug}`}
					class="inline-flex items-center gap-1.5 rounded-full border bg-card px-3 py-1.5 text-sm shadow-sm transition-colors hover:bg-muted"
				>
					<Coffee size={14} class="text-muted-foreground" />
					{cr.name}
					<span class="text-muted-foreground text-xs">{cr.count}</span>
				</a>
			{/each}
		</div>
		<TastingSessionList
			sessions={filteredTastings}
			emptyTitle="No sessions found"
			emptyDescription={`You haven't recorded any tastings for ${roasterName} yet.`}
		/>
	{:else}
		<TastingSessionList
			sessions={filteredTastings}
			emptyTitle="No sessions found"
			emptyDescription={`You haven't recorded any tastings for ${roasterName} yet.`}
		/>
	{/if}
</div>
