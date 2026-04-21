<script lang="ts">
	import { Card } from "$lib/components/ui/card";
	import { Input } from "$lib/components/ui/input";
	import { cn, getFlavourCategoryColors } from "$lib/utils";
	import {
		TASTE_BASICS_QUESTIONS,
		MOUTHFEEL_QUESTIONS,
		TASTING_CONVERSATION,
		DEFECT_CONVERSATION,
		type TastingConversationCategory,
	} from "$lib/tasting/conversation";
	import { noteToCategoryMap } from "$lib/stores/tastingNotesStore.svelte";
	import SortableNote from "./SortableNote.svelte";
	import CoffeeBeanTile from "./CoffeeBeanTile.svelte";
	import { DragDropProvider, DragOverlay } from "@dnd-kit-svelte/svelte";
	import { tick, type Snippet } from "svelte";
	import RemoveNoteDropZone from "./RemoveNoteDropZone.svelte";
	import { Button } from "$lib/components/ui/button";
	import BeanSearchCombobox from "./BeanSearchCombobox.svelte";
	import { api, type CoffeeBean } from "$lib/api";
	import { Sparkles, Trash2 } from "lucide-svelte";

	interface Props {
		sessionName?: string;
		brewingNotes?: string;
		basics: Record<string, string>;
		mouthfeel: Record<string, string>;
		allSelectedNotesList: string[];
		readonly?: boolean;
		class?: string;
		date?: Date;
		onDelete?: () => void;
		footer?: Snippet;
		// Optional Props (needed for interactive wizard summary, but optional for history)
		selectedCategoryIds?: string[];
		tastingConversation?: TastingConversationCategory[];
		selectedSubCategoryIds?: Record<string, string[]>;
		selectedNotes?: Record<string, string[]>;
		isSummaryStep?: boolean;
		/** Bindable: the parent can hold a reference to call this on save to get the current drag-sorted order */
		getOrderedNotes?: () => string[];
		onRemoveNote?: (note: string) => void;
		beanUrlPath?: string | null;
		beanLabel?: string | null;
		beanData?: CoffeeBean | null;
		savedBeanPaths?: string[];
	}

	let {
		sessionName = $bindable(""),
		brewingNotes = $bindable(""),
		basics,
		mouthfeel,
		allSelectedNotesList = $bindable([]),
		readonly = false,
		class: className = "",
		date,
		onDelete,
		footer,
		selectedCategoryIds: propSelectedCategoryIds,
		tastingConversation: propTastingConversation,
		selectedSubCategoryIds: propSelectedSubCategoryIds,
		selectedNotes: propSelectedNotes,
		isSummaryStep = false,
		getOrderedNotes = $bindable<() => string[]>(),
		onRemoveNote,
		beanUrlPath = $bindable(null),
		beanLabel = $bindable(null),
		beanData = $bindable(null),
		savedBeanPaths = [],
	}: Props = $props();

	// Registry: note → getter for its current sortable index (updated by dnd-kit's OptimisticSortingPlugin)
	const sortableRegistry = new Map<string, () => { index: number }>();

	function registerSortable(
		note: string,
		getInstance: () => { index: number },
	) {
		sortableRegistry.set(note, getInstance);
	}

	$effect(() => {
		getOrderedNotes = () =>
			[...allSelectedNotesList].sort((a, b) => {
				const ia = sortableRegistry.get(a)?.()?.index ?? 999;
				const ib = sortableRegistry.get(b)?.()?.index ?? 999;
				return ia - ib;
			});
	});

	// If readonly, we reconstruct the categorized view from the flat allSelectedNotesList
	// This makes using the component in history pages much easier
	const displayData = $derived.by(() => {
		// Priority: Use the custom ordered list if we're not regrouping everything
		const effectiveNotesList =
			allSelectedNotesList.length > 0 ? allSelectedNotesList : [];

		// Use props if provided (Wizard case), otherwise reconstruct (History case)
		if (
			!readonly &&
			propSelectedCategoryIds &&
			propSelectedNotes &&
			propSelectedSubCategoryIds
		) {
			return {
				categoryIds: propSelectedCategoryIds,
				notes: propSelectedNotes,
				subCategoryIds: propSelectedSubCategoryIds,
				conversation: propTastingConversation || TASTING_CONVERSATION,
			};
		}

		// Reconstruction Logic for History/Readonly mode
		const conversation = propTastingConversation || TASTING_CONVERSATION;
		const categories = [...conversation, ...DEFECT_CONVERSATION];
		const categoryIds: string[] = [];
		const notes: Record<string, string[]> = {};
		const subCategoryIds: Record<string, string[]> = {};

		// If we HAVE an allSelectedNotesList (like in history), we should respect its order
		// while still identifying categories for styling
		for (const noteName of effectiveNotesList) {
			const cat = categories.find(
				(c) =>
					c.name === noteName ||
					c.flavors?.some(
						(f) =>
							(typeof f === "string" ? f : f.name) === noteName,
					) ||
					c.subTypes?.some(
						(s) =>
							s.name === noteName ||
							s.flavors.some(
								(f) =>
									(typeof f === "string" ? f : f.name) ===
									noteName,
							),
					),
			);

			// ... Rest of reconstruction ...
			if (cat) {
				const targetCatId = cat.isDefect ? "defects" : cat.id;
				if (
					targetCatId !== "defects" &&
					!categoryIds.includes(targetCatId)
				) {
					categoryIds.push(targetCatId);
				}

				const sub = cat.subTypes?.find(
					(s) =>
						s.name === noteName ||
						s.flavors.some(
							(f) =>
								(typeof f === "string" ? f : f.name) ===
								noteName,
						),
				);

				if (sub) {
					if (!subCategoryIds[targetCatId])
						subCategoryIds[targetCatId] = [];
					if (!subCategoryIds[targetCatId].includes(sub.id)) {
						subCategoryIds[targetCatId].push(sub.id);
					}

					const isSpecificFlavor =
						sub.flavors.some(
							(f) =>
								(typeof f === "string" ? f : f.name) ===
								noteName,
						) && noteName !== sub.name;
					if (isSpecificFlavor) {
						if (!notes[targetCatId]) notes[targetCatId] = [];
						if (!notes[targetCatId].includes(noteName))
							notes[targetCatId].push(noteName);
					}
				} else {
					const isSpecificFlavor =
						cat.flavors?.some(
							(f) =>
								(typeof f === "string" ? f : f.name) ===
								noteName,
						) && noteName !== cat.name;
					if (isSpecificFlavor) {
						if (!notes[targetCatId]) notes[targetCatId] = [];
						if (!notes[targetCatId].includes(noteName))
							notes[targetCatId].push(noteName);
					}
				}
			} else {
				// Fallback: try the API's note-to-category map (primaryCategory is the category name e.g. "Fruity")
				const apiCategoryName =
					noteToCategoryMap[noteName.toLowerCase()];
				const apiCat = apiCategoryName
					? conversation.find(
							(c) =>
								c.name.toLowerCase() ===
								apiCategoryName.toLowerCase(),
						)
					: null;

				if (apiCat) {
					const targetCatId = apiCat.id;
					if (!categoryIds.includes(targetCatId))
						categoryIds.push(targetCatId);
					if (!notes[targetCatId]) notes[targetCatId] = [];
					if (!notes[targetCatId].includes(noteName))
						notes[targetCatId].push(noteName);
				} else {
					// Last resort: unknown note goes into a catch-all bucket
					if (!notes["other"]) notes["other"] = [];
					if (!notes["other"].includes(noteName))
						notes["other"].push(noteName);
					if (!categoryIds.includes("other"))
						categoryIds.push("other");
				}
			}
		}

		// Ensure "Other" category is in the conversation if needed for display
		const finalConversation =
			categoryIds.includes("other") &&
			!conversation.some((c) => c.id === "other")
				? [
						...conversation,
						{
							id: "other",
							name: "Other",
							emoji: "☕",
							question: "",
							flavors: [],
						},
					]
				: conversation;

		return {
			categoryIds,
			notes,
			subCategoryIds,
			conversation: finalConversation,
			orderedNotes: effectiveNotesList,
		};
	});

	function getCategoryForNote(noteName: string) {
		const categories = [...TASTING_CONVERSATION, ...DEFECT_CONVERSATION];
		return categories.find(
			(c) =>
				c.name === noteName ||
				c.flavors?.some(
					(f) => (typeof f === "string" ? f : f.name) === noteName,
				) ||
				c.subTypes?.some(
					(s) =>
						s.name === noteName ||
						s.flavors.some(
							(f) =>
								(typeof f === "string" ? f : f.name) ===
								noteName,
						),
				),
		);
	}
	let isDragging = $state(false);
	let activeNote = $state<string | null>(null);

	function handleDragStart(event: any) {
		isDragging = true;
		activeNote = event.operation.source.id;
	}

	function handleDragEnd(event: any) {
		const op = event.operation;
		isDragging = false;
		activeNote = null;
		if (op?.target?.id === "trash") {
			const noteToRemove = op.source.id;
			sortableRegistry.delete(noteToRemove);
			allSelectedNotesList = allSelectedNotesList.filter(
				(n) => n !== noteToRemove,
			);
			onRemoveNote?.(noteToRemove);
		}
	}
</script>

<Card
	class={cn("shadow-xl p-6 sm:p-8 border-dashed w-full max-w-2xl", className)}
>
	<div class="gap-8 grid">
		{#if readonly && (sessionName || date || onDelete)}
			<div class="flex justify-between items-start">
				<div class="space-y-1">
					{#if sessionName || readonly}
						<h3 class="font-black text-2xl tracking-tighter">
							{sessionName || "Tasting Session"}
						</h3>
					{/if}
					{#if date}
						<p
							class="font-black text-muted-foreground text-xs uppercase tracking-[0.2em]"
						>
							{new Intl.DateTimeFormat("en-GB", {
								dateStyle: "full",
								timeStyle: "short",
							}).format(date)}
						</p>
					{/if}
				</div>
				{#if onDelete}
					<Button
						variant="ghost"
						size="icon"
						class="-mr-2 text-muted-foreground hover:text-destructive shrink-0"
						onclick={onDelete}
					>
						<Trash2 size={18} />
					</Button>
				{/if}
			</div>
		{/if}

		{#if !readonly}
			<div class="space-y-3 text-left">
				<label
					for="session-name"
					class="ml-1 font-bold text-muted-foreground text-xs uppercase tracking-widest"
				>
					Session Name (Optional)
				</label>
				<Input
					id="session-name"
					placeholder="Ethiopia Gesha Natural, Colombia Pink Bourbon, Morning V60, etc"
					bind:value={sessionName}
					class="bg-background shadow-sm h-12 text-lg"
				/>
			</div>

			<div class="space-y-3 text-left">
				<label
					for="bean-search"
					class="ml-1 font-bold text-muted-foreground text-xs uppercase tracking-widest"
				>
					Coffee Bean (Optional)
				</label>
				<BeanSearchCombobox
					bind:value={beanUrlPath}
					bind:beanLabel={beanLabel}
					bind:selectedBean={beanData}
					{savedBeanPaths}
				/>
			</div>

			<div class="space-y-3 text-left">
				<label
					for="brewing-notes"
					class="ml-1 font-bold text-muted-foreground text-xs uppercase tracking-widest"
				>
					Brewing Notes (Optional)
				</label>
				<textarea
					id="brewing-notes"
					placeholder="V60, 15g in / 250g out, 94°C, 2:30 total time..."
					bind:value={brewingNotes}
					class="bg-background shadow-sm p-3 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary/20 w-full min-h-[100px] text-lg transition-all"
				></textarea>
			</div>
		{:else if brewingNotes || (readonly && beanUrlPath)}
			<div class="space-y-4">
				{#if readonly && beanData}
					<CoffeeBeanTile bean={beanData} size="sm" />
				{:else if readonly && beanLabel}
					<div class="bg-emerald-50/10 px-3 py-2 border border-emerald-500/10 rounded-lg">
						<p class="mb-0.5 font-bold text-[10px] text-emerald-600 uppercase tracking-wider">Selected Bean</p>
						<p class="font-bold text-foreground text-sm truncate">{beanLabel}</p>
					</div>
				{/if}

				{#if brewingNotes}
					<div class="bg-muted/30 p-4 border border-dashed rounded-xl text-sm">
						<p
							class="mb-1 font-bold text-[10px] text-muted-foreground uppercase tracking-widest"
						>
							Brewing Notes
						</p>
						<p class="whitespace-pre-wrap">{brewingNotes}</p>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Notes -->
		<div class="space-y-6">
			{#if allSelectedNotesList.length > 0}
				<div class="flex flex-col gap-4">
					{#if isSummaryStep && !readonly}
						<div
							class="flex items-center gap-2 font-bold text-muted-foreground text-xs uppercase tracking-widest"
						>
							<span>✨</span> Reorder by prominence (Drag to sort)
						</div>
						<DragDropProvider
							onDragStart={handleDragStart}
							onDragEnd={handleDragEnd}
						>
							<div class="flex flex-wrap gap-2">
								{#each allSelectedNotesList as note, index (note)}
									{@const cat = getCategoryForNote(note)}
									{@const colors = getFlavourCategoryColors(
										cat?.isDefect
											? "defects"
											: cat?.name || "Other",
									)}
									<SortableNote
										{note}
										{index}
										{colors}
										isDefect={cat?.isDefect}
										onRegister={registerSortable}
									/>
								{/each}
							</div>

							<DragOverlay>
								{#if activeNote}
									{@const cat = getCategoryForNote(activeNote)}
									{@const colors = getFlavourCategoryColors(
										cat?.isDefect
											? "defects"
											: cat?.name || "Other",
									)}
									<div
										class={cn(
											"flex items-center gap-2 shadow-xl px-3 py-2 border rounded-full font-medium text-sm scale-105 pointer-events-none",
											cat?.isDefect
												? "border-destructive/30 bg-destructive/10 text-destructive"
												: cn(
														colors.bg,
														colors.text,
														colors.border,
														colors.darkBg,
														colors.darkText,
														colors.darkBorder,
													),
										)}
									>
										<span class="opacity-40 shrink-0"
											>⠿</span
										>
										{activeNote}
									</div>
								{/if}
							</DragOverlay>

							<RemoveNoteDropZone active={isDragging} />
						</DragDropProvider>
					{:else}
						<div class="flex flex-wrap gap-2">
							{#each allSelectedNotesList as note}
								{@const cat = getCategoryForNote(note)}
								{@const colors = getFlavourCategoryColors(
									cat?.isDefect
										? "defects"
										: cat?.name || "Other",
								)}
								<span
									class={cn(
										"shadow-sm px-3 py-1 border rounded-full font-medium text-sm",
										cat?.isDefect
											? "border-destructive/30 bg-destructive/10 text-destructive"
											: cn(
													colors.bg,
													colors.text,
													colors.border,
													colors.darkBg,
													colors.darkText,
													colors.darkBorder,
												),
									)}
								>
									{note}
								</span>
							{/each}
						</div>
					{/if}
				</div>
			{/if}

			{#if allSelectedNotesList.length === 0}
				<p class="py-4 text-muted-foreground text-center italic">
					No specific flavours selected
				</p>
			{/if}
		</div>

		<div class="gap-4 grid grid-cols-2 pt-6 border-t text-sm">
			<div class="space-y-4">
				<p
					class="font-bold text-muted-foreground/60 text-xs uppercase tracking-widest"
				>
					Basics
				</p>
				{#each Object.entries(basics) as [id, val]}
					<div class="flex justify-between pb-1 border-muted border-b">
						<span class="text-muted-foreground"
							>{TASTE_BASICS_QUESTIONS.find((q) => q.id === id)
								?.name}</span
						>
						<span class="font-semibold">{val}</span>
					</div>
				{/each}
			</div>
			<div class="space-y-4">
				<p
					class="font-bold text-muted-foreground/60 text-xs uppercase tracking-widest"
				>
					Body & Finish
				</p>
				{#each Object.entries(mouthfeel) as [id, val]}
					<div class="flex justify-between pb-1 border-muted border-b">
						<span class="text-muted-foreground"
							>{MOUTHFEEL_QUESTIONS.find((q) => q.id === id)
								?.name}</span
						>
						<span class="font-semibold">{val}</span>
					</div>
				{/each}
			</div>
		</div>

		{#if footer}
			<div class="flex flex-wrap justify-center gap-2 pt-2">
				{@render footer()}
			</div>
		{/if}
	</div>
</Card>
