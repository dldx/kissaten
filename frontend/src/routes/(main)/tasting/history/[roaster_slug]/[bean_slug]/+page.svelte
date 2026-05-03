<script lang="ts">
	import { onMount } from "svelte";
	import { page } from "$app/state";
        import { getTastingHistory, type TastingSession } from "$lib/db/localdb";
        import TastingSummaryCard from "$lib/components/tasting/TastingSummaryCard.svelte";
        import { Button } from "$lib/components/ui/button";
        import { Card } from "$lib/components/ui/card";
        import { Search, Clipboard, Image as ImageIcon, Share2, Coffee } from "lucide-svelte";
        import { mode } from "mode-watcher";
        import {
                exportTastingAsImage,
                getTastingSearchUrl,
                copyTastingToClipboard,
                deleteTasting,
                getHistoryUrl
        } from "$lib/utils/tasting_utils";
    import SaveBeanButton from "$lib/components/vault/SaveBeanButton.svelte";

        const roasterSlug = $derived(page.params.roaster_slug || "");
        const beanSlug = $derived(page.params.bean_slug || "");
        const currentBeanUrlPath = $derived(`/${roasterSlug}/${beanSlug}`);

        let tastingHistory = $state<TastingSession[]>([]);
        let isLoading = $state(true);
        let canShareImage = $state(false);

        const filteredTastings = $derived(
                tastingHistory.filter(t => t.beanUrlPath === currentBeanUrlPath)
        );

        const beanName = $derived(filteredTastings[0]?.beanName || beanSlug.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '));
        const roasterName = $derived(filteredTastings[0]?.roasterName || roasterSlug.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '));

        onMount(async () => {
                tastingHistory = await getTastingHistory();
                isLoading = false;

                try {
                        canShareImage =
                                !!navigator.share &&
                                !!navigator.canShare &&
                                navigator.canShare({
                                        files: [new File([], "t.png", { type: "image/png" })],
                                });
                } catch (e) {
                        canShareImage = false;
                }
        });

    const beanData = $derived(filteredTastings[0]?.beanData || null);
</script>
<svelte:head>
	<title>{beanName} | {roasterName} | Tasting History | Kissaten</title>
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
				<p class="text-muted-foreground">You haven't recorded any tastings for this bean yet.</p>
			</div>
			<Button href="/tasting">New guided tasting</Button>
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

