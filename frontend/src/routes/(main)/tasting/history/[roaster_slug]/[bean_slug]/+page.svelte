<script lang="ts">
	import { page } from "$app/state";
	import { getTastingHistory, db, type TastingSession } from "$lib/db/localdb";
	import { dbUpdateTrigger } from "$lib/db/updates.svelte";
	import { Button } from "$lib/components/ui/button";
	import TastingSessionList from "$lib/components/tasting/TastingSessionList.svelte";
	import { Calendar, Plus } from "lucide-svelte";
	import { slugifyCustomRoaster, getCustomRoasterName } from "$lib/utils/tasting_utils";

	const roasterSlug = $derived(page.params.roaster_slug || "");
	const beanSlug = $derived(page.params.bean_slug || "");
	const currentBeanUrlPath = $derived(`/${roasterSlug}/${beanSlug}`);
	const isCustomNamespace = $derived(roasterSlug === "custom");

	let tastingHistory = $state<TastingSession[]>([]);
	let isLoading = $state(true);
	// "bean" => this is a single custom bean's history; "roaster" => a
	// custom-roaster grouping page; "unset" => decision pending after load.
	let mode = $state<"unset" | "bean" | "roaster">("unset");

	const filteredTastings = $derived(
		mode === "bean"
			? tastingHistory.filter((t) => t.beanUrlPath === currentBeanUrlPath)
			: tastingHistory.filter(
					(t) =>
						t.beanUrlPath?.startsWith("/custom/") &&
						slugifyCustomRoaster(getCustomRoasterName(t)) === beanSlug,
			  ),
	);

	const beanName = $derived(
		filteredTastings[0]?.beanName ||
			beanSlug.split(/[_-]+/).map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" "),
	);
	const roasterName = $derived(
		filteredTastings[0]?.roasterName ||
			roasterSlug.split(/[_-]+/).map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" "),
	);

	$effect(() => {
		const trigger = dbUpdateTrigger.tastingHistory;
		void refresh();
	});

	async function refresh() {
		tastingHistory = await getTastingHistory();

		if (isCustomNamespace) {
			// Disambiguate: if the slug refers to an actual custom bean, show its
			// single-bean history; otherwise treat the slug as a roaster group.
			const isBean =
				tastingHistory.some((t) => t.beanUrlPath === currentBeanUrlPath) ||
				(await db.customBeans.where("syncId").equals(beanSlug).count()) > 0;
			mode = isBean ? "bean" : "roaster";
		} else {
			mode = "bean";
		}

		isLoading = false;
	}
</script>

<svelte:head>
	<title>{beanName} | {roasterName} | Tasting History | Kissaten</title>
	<meta
		name="description"
		content="Tasting history for {beanName} roasted by {roasterName}."
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

	{#if isLoading || mode === "unset"}
		<div class="space-y-3" aria-busy="true">
			{#each Array(6) as _}
				<div class="bg-muted rounded-xl w-full h-20 animate-pulse"></div>
			{/each}
		</div>
	{:else}
		<TastingSessionList
			sessions={filteredTastings}
			emptyTitle="No sessions found"
			emptyDescription={mode === "roaster"
				? `You haven't recorded any tastings for this roaster's beans yet.`
				: `You haven't recorded any tastings for this bean yet.`}
		/>
	{/if}
</div>
