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

	async function remove(id: number | undefined) {
		if (id === undefined) return;
		if (confirm("Are you sure you want to delete this session?")) {
			await deleteTasting(id);
			tastingHistory = tastingHistory.filter((t) => t.id !== id);
		}
	}

	async function copyAsImage(session: TastingSession) {
		const options: TastingImageOptions = {
			sessionName: session.name || "Coffee Tasting Session",
			dateOrNotes:
				session.brewingNotes ||
				new Intl.DateTimeFormat("en-GB", {
					dateStyle: "full",
				}).format(session.date),
			basics: session.basics || {},
			mouthfeel: session.mouthfeel || {},
			allSelectedNotesList: session.selectedNotes || [],
			beanData: session.beanData,
			isDarkMode: mode.current === "dark",
		};

		await copyTastingAsImage(options, session.name || "");
	}

	async function copyToClipboard(session: TastingSession) {
		try {
			const options: TastingImageOptions = {
				sessionName: session.name || "Coffee Tasting Session",
				dateOrNotes:
					session.brewingNotes ||
					new Intl.DateTimeFormat("en-GB", {
						dateStyle: "full",
					}).format(session.date),
				basics: session.basics || {},
				mouthfeel: session.mouthfeel || {},
				allSelectedNotesList: session.selectedNotes || [],
				beanData: session.beanData,
			};
			const text = generateTastingText(options);

			if (navigator.clipboard?.writeText) {
				await navigator.clipboard.writeText(text);
				toast.success("Summary copied to clipboard!");
			} else if (navigator.share) {
				await navigator.share({
					title: options.sessionName,
					text: text,
				});
			} else {
				// Legacy fallback for non-secure contexts or older browsers
				const textArea = document.createElement("textarea");
				textArea.value = text;
				textArea.style.position = "fixed";
				textArea.style.left = "-9999px";
				textArea.style.top = "0";
				document.body.appendChild(textArea);
				textArea.focus();
				textArea.select();
				try {
					const successful = document.execCommand("copy");
					if (successful) {
						toast.success("Summary copied to clipboard!");
					} else {
						throw new Error("copy command failed");
					}
				} catch (err) {
					throw new Error("Legacy copy failed");
				} finally {
					document.body.removeChild(textArea);
				}
			}
		} catch (e) {
			console.error("Failed to copy text", e);
			toast.error("Failed to copy to clipboard");
		}
	}
</script>

<svelte:head>
	<title>Tasting History | Kissaten</title>
</svelte:head>

<div class="mx-auto mb-24 px-4 py-12 max-w-4xl container">
	<div class="flex justify-between items-center mb-12">
		<div class="flex flex-col gap-2">
			<a
				href="/tasting"
				class="flex items-center gap-1 text-muted-foreground hover:text-primary text-sm transition-colors"
			>
				<ChevronLeft size={14} /> Back to Tasting Guide
			</a>
			<h1 class="font-black text-4xl tracking-tighter">
				Tasting History
			</h1>
		</div>
		<div
			class="flex items-center gap-2 bg-primary/10 px-4 py-2 border border-primary/20 rounded-full font-bold text-primary text-sm"
		>
			<Calendar size={16} />
			{tastingHistory.length} Sessions
		</div>
	</div>

	{#if isLoading}
		<div class="space-y-6">
			{#each Array(3) as _}
				<div
					class="bg-muted rounded-2xl w-full h-48 animate-pulse"
				></div>
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
			<Button href="/tasting">Start a New Tasting</Button>
		</Card>
	{:else}
		<div class="gap-8 grid">
			{#each tastingHistory as session (session.id)}
				<div transition:fade>
					<TastingSummaryCard
						readonly
						sessionName={session.name}
						date={session.date}
						onDelete={() => remove(session.id)}
						allSelectedNotesList={session.selectedNotes}
						basics={session.basics || {}}
						mouthfeel={session.mouthfeel || {}}
						brewingNotes={session.brewingNotes}
						beanUrlPath={session.beanUrlPath}
						beanLabel={session.beanLabel}
						beanData={session.beanData}
					>
						{#snippet footer()}
							<Button
								size="sm"
								variant="ghost"
								class="gap-2 text-muted-foreground"
								onclick={() => copyToClipboard(session)}
							>
								<Clipboard size={14} /> Copy Text
							</Button>
							<Button
								size="sm"
								variant="ghost"
								class="gap-2"
								onclick={() => copyAsImage(session)}
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
