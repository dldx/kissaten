<script lang="ts">
	import { onMount } from "svelte";
	import { page } from "$app/state";
	import { getTasting, type TastingSession } from "$lib/db/localdb";
	import TastingSummaryCard from "$lib/components/tasting/TastingSummaryCard.svelte";
	import { Button } from "$lib/components/ui/button";
	import { Clipboard, Image as ImageIcon, Share2, Search, Coffee } from "lucide-svelte";
	import { mode } from "mode-watcher";
	import {
		exportTastingAsImage,
		getTastingSearchUrl,
		copyTastingToClipboard,
		deleteTasting,
		prewarmTastingImage,
	} from "$lib/utils/tasting_utils";

	let session = $state<TastingSession | undefined>(undefined);
	let isLoading = $state(true);
	let canShareImage = $state(false);

	onMount(async () => {
		const tastingId = page.params.tasting_id;
		if (tastingId) {
			const id = parseInt(tastingId);
			if (!isNaN(id)) {
				session = await getTasting(id);
			}
		}
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

		if (session) {
			// Pre-warm the image cache so the native share sheet opens on the first
			// tap (navigator.share requires an active user gesture).
			prewarmTastingImage({
				sessionName: session.name || "Coffee Tasting",
				dateOrNotes:
					session.brewingNotes ||
					new Intl.DateTimeFormat("en-GB", { dateStyle: "full" }).format(session.date),
				basics: session.basics || {},
				mouthfeel: session.mouthfeel || {},
				allSelectedNotesList: session.selectedNotes || [],
				beanData: session.beanData,
				isDarkMode: mode.current === "dark",
			});
		}
	});
</script>

<svelte:head>
	<title>{session?.name || "Tasting Session"} | Kissaten</title>
	<meta
		name="description"
		content="Detailed view of a coffee tasting session."
	/>
	<meta name="robots" content="noindex,follow" />
</svelte:head>

<div class="mb-24">
	{#if isLoading}
		<div class="bg-muted rounded-2xl w-full h-[600px] animate-pulse"></div>
	{:else if session}
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
				await deleteTasting(session?.id, { goBack: true });
			}}
		>
			{#snippet title(name: string | undefined)}
				<h1 class="font-black text-2xl tracking-tighter">
					{name || "Tasting Session"}
				</h1>
			{/snippet}

			{#snippet footer()}
				<div class="flex flex-wrap gap-2 w-full">
					<div class="grid grid-cols-3 gap-2 w-full sm:contents sm:flex sm:flex-wrap sm:gap-2">
						<Button
							size="sm"
							variant="outline"
							class="gap-2 justify-center"
							onclick={() => copyTastingToClipboard(session!)}
						>
							<Clipboard size={14} /> Copy Text
						</Button>
						<Button
							size="sm"
							variant="outline"
							class="gap-2 justify-center"
							onclick={() => exportTastingAsImage(session!, mode.current === "dark")}
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
							class="gap-2 justify-center"
							href={getTastingSearchUrl(session!.selectedNotes)}
						>
							<Search size={14} /> Find Matches
						</Button>
					</div>
					{#if session!.beanUrlPath}
						<Button
							size="sm"
							variant="default"
							class="gap-2 justify-center w-full sm:w-auto sm:ml-auto"
							href={`/roasters${session!.beanUrlPath}`}
						>
							<Coffee size={14} /> View Bean
						</Button>
					{/if}
				</div>
			{/snippet}
		</TastingSummaryCard>
	{:else}
		<div class="py-24 text-center">
			<h1 class="mb-4 font-bold text-2xl">Session not found</h1>
			<p class="mb-8 text-muted-foreground">This tasting session may have been deleted.</p>
			<Button href="/tasting/history">Go to History</Button>
		</div>
	{/if}
</div>
