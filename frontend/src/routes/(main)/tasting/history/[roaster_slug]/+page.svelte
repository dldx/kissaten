 <script lang="ts">
	import { onMount } from "svelte";
	import { page } from "$app/state";
	import { getTastingHistory, type TastingSession } from "$lib/db/localdb";
	import TastingSummaryCard from "$lib/components/tasting/TastingSummaryCard.svelte";
	import BackButton from "$lib/components/BackButton.svelte";
	import { Button } from "$lib/components/ui/button";
	import { Card } from "$lib/components/ui/card";
	import { Search, Clipboard, Image as ImageIcon, Share2 } from "lucide-svelte";
	import { mode } from "mode-watcher";
	import {
		exportTastingAsImage,
		getTastingSearchUrl,
		copyTastingToClipboard,
		deleteTasting,
		getHistoryUrl
	} from "$lib/utils/tasting_utils";
	import { KissatenAPI } from "$lib/api";

	const roasterSlug = $derived(page.params.roaster_slug || "");
	const api = new KissatenAPI();

	let tastingHistory = $state<TastingSession[]>([]);
	let isLoading = $state(true);
	let roasterName = $state<string>("");
	let canShareImage = $state(false);

	const filteredTastings = $derived(
		tastingHistory.filter(t => {
			if (!t.beanUrlPath) return false;
			const parts = t.beanUrlPath.split('/').filter(Boolean);
			return parts[0] === roasterSlug;
		})
	);

	onMount(async () => {
		try {
			const [history, response] = await Promise.all([
				getTastingHistory(),
				api.getRoasters()
			]);
			tastingHistory = history;

			const roasters = response.data || [];
			const roaster = roasters.find(r => r.slug === roasterSlug);
			if (roaster) {
				roasterName = roaster.name;
			} else {
				// Fallback to slug if roaster not found
				roasterName = roasterSlug.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
			}
		} catch (error) {
			console.error("Failed to load tasting history or roasters:", error);
		} finally {
			isLoading = false;
		}
	});
</script>

<svelte:head>
	<title>{roasterName} Tasting History | Kissaten</title>
	<meta
		name="description"
		content="View all coffee tasting sessions for {roasterName}."
	/>
	<meta name="robots" content="noindex,follow" />
</svelte:head>

<div class="mx-auto mb-24 px-4 py-12 max-w-4xl container">

	{#if isLoading}
		<div class="space-y-4">
			{#each Array(3) as _}
				<div class="bg-muted rounded-2xl w-full h-48 animate-pulse"></div>
			{/each}
		</div>
	{:else if filteredTastings.length === 0}
		<Card class="flex flex-col items-center gap-4 py-24 text-center">
			<div class="bg-muted p-4 rounded-full">
				<Search class="w-8 h-8 text-muted-foreground" />
			</div>
			<div>
				<h2 class="font-bold text-xl">No sessions found</h2>
				<p class="text-muted-foreground">You haven't recorded any tastings for {roasterName} yet.</p>
			</div>
			<Button href="/tasting" size="lg" class="mt-4 rounded">New guided tasting</Button>
		</Card>
	{:else}
		<div class="flex flex-col gap-8">
			{#each filteredTastings as session (session.id)}
				<TastingSummaryCard
					readonly
					sessionName={session.name}
					date={session.date}
					allSelectedNotesList={session.selectedNotes}
					basics={session.basics || {}}
					mouthfeel={session.mouthfeel || {}}
					brewingNotes={session.brewingNotes}
					beanUrlPath={session.beanUrlPath}
					beanName={session.beanName}
					roasterName={session.roasterName}
					beanData={session.beanData}
					onDelete={async () => {
						await deleteTasting(session.id, {
							onSuccess: () => {
								tastingHistory = tastingHistory.filter((t) => t.id !== session.id);
							}
						});
					}}
				>
					{#snippet title(name: string | undefined)}
						<a
							href={getHistoryUrl(session)}
							class="group/title block"
						>
							<h3
								class="font-black group-hover/title:text-cyan-400 text-2xl tracking-tighter transition-colors"
							>
								{name || "Tasting Session"}
							</h3>
						</a>
					{/snippet}

					{#snippet footer()}
						<div class="flex flex-wrap gap-2">
							<Button
								size="sm"
								variant="outline"
								class="gap-2"
								href={getHistoryUrl(session)}
							>
								View Full Session
							</Button>
							<Button
								size="sm"
								variant="outline"
								class="gap-2"
								onclick={() => copyTastingToClipboard(session)}
							>
								<Clipboard size={14} /> Copy Text
							</Button>
							<Button
								size="sm"
								variant="outline"
								class="gap-2"
								onclick={() => exportTastingAsImage(session, mode.current === "dark")}
							>
								{#if canShareImage}
									<Share2 size={14} /> Share
								{:else}
									<ImageIcon size={14} /> Save as Image
								{/if}
							</Button>
							<Button
								size="sm"
								variant="outline"
								class="gap-2"
								href={getTastingSearchUrl(session.selectedNotes)}
							>
								<Search size={14} /> Find Matches
							</Button>
						</div>
					{/snippet}
				</TastingSummaryCard>
			{/each}
		</div>
	{/if}
</div>
