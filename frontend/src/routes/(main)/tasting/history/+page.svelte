<script lang="ts">
	import { onMount } from "svelte";
	import {
		getTastingHistory,
		deleteTasting,
		type TastingSession,
	} from "$lib/db/localdb";
	import TastingSummaryCard from "$lib/components/tasting/TastingSummaryCard.svelte";
	import { Button } from "$lib/components/ui/button";
	import { Card } from "$lib/components/ui/card";
	import {
		Search,
		Calendar,
		ChevronLeft,
		Image as ImageIcon,
		Clipboard,
		Share2,
	} from "lucide-svelte";
	import { fade } from "svelte/transition";
	import {
		generateTastingImage,
		generateTastingText,
		type TastingImageOptions,
	} from "$lib/utils/imageGenerator";
	import { copyTastingAsImage, getTastingSearchUrl } from "$lib/utils/tasting_utils";
	import { toast } from "svelte-sonner";
	import { mode } from "mode-watcher";
	import { page } from "$app/state";
	import {
		exportTastingAsImage,
		copyTastingToClipboard,
		getHistoryUrl
	} from "$lib/utils/tasting_utils";
	import BackButton from "$lib/components/BackButton.svelte";

	let tastingHistory = $state<TastingSession[]>([]);
	let isLoading = $state(true);
	let canShareImage = $state(false);

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
</script>

<svelte:head>
	<title>Tasting History | Kissaten</title>
</svelte:head>

<div class="mx-auto mb-24 px-4 py-12 max-w-4xl container">
	<div class="flex justify-between items-center mb-6">
		<div
			class="flex items-center gap-2 bg-primary/10 px-4 py-2 border border-primary/20 rounded-full font-bold text-primary text-sm"
		>
			<Calendar size={16} />
			{tastingHistory.length} Session{tastingHistory.length !== 1 ? "s" : ""}
		</div>
	</div>

	{#if isLoading}
		<div class="space-y-6">
			{#each Array(3) as _}
				<div class="bg-muted rounded-2xl w-full h-48 animate-pulse"></div>
			{/each}
		</div>
	{:else if tastingHistory.length === 0}
		<Card
			class="flex flex-col items-center gap-6 p-12 border-dashed text-center"
		>
			<div class="bg-muted p-6 rounded-full">
				<Search size={48} class="text-muted-foreground/30" />
			</div>
			<div class="space-y-2">
				<h2 class="font-bold text-xl">No sessions found</h2>
				<p class="text-muted-foreground">
					Your guided tasting results will appear here once saved.
				</p>
			</div>
			<Button
				href={"/tasting"}
			>
				New Guided Tasting
			</Button>
		</Card>
	{:else}
		<div class="gap-8 grid">
			{#each tastingHistory as session (session.id)}
				<div transition:fade>
					<TastingSummaryCard
						readonly
						sessionName={session.name}
						date={session.date}
					onDelete={async () => {
						if (session.id) {
							await deleteTasting(session.id);
							tastingHistory = tastingHistory.filter((t) => t.id !== session.id);
							toast.success("Tasting session deleted");
						}
					}}
						allSelectedNotesList={session.selectedNotes}
						basics={session.basics || {}}
						mouthfeel={session.mouthfeel || {}}
						brewingNotes={session.brewingNotes}
						beanUrlPath={session.beanUrlPath}
						beanName={session.beanName}
						roasterName={session.roasterName}
						beanData={session.beanData}
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
							<Button
								size="sm"
								variant="ghost"
								class="gap-2 text-muted-foreground"
								onclick={() => copyTastingToClipboard(session)}
							>
								<Clipboard size={14} /> Copy Text
							</Button>
							<Button
								size="sm"
								variant="ghost"
								class="gap-2"
								onclick={() => exportTastingAsImage(session, mode.current === "dark")}
							>
								{#if canShareImage}
									<Share2 size={14} /> Share
								{:else}
									<ImageIcon size={14} /> Copy as Image
								{/if}
							</Button>
							<Button
								size="sm"
								variant="ghost"
								class="gap-2"
								href={getTastingSearchUrl(session.selectedNotes)}
							>
								<Search size={14} /> Find matching beans
							</Button>
						{/snippet}
					</TastingSummaryCard>
				</div>
			{/each}
		</div>
	{/if}
</div>
