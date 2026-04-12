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

	interface Props {
		sessionName?: string;
		brewingNotes?: string;
		basics: Record<string, string>;
		mouthfeel: Record<string, string>;
		allSelectedNotesList: string[];
		readonly?: boolean;
		class?: string;
		// Optional Props (needed for interactive wizard summary, but optional for history)
		selectedCategoryIds?: string[];
		tastingConversation?: TastingConversationCategory[];
		selectedSubCategoryIds?: Record<string, string[]>;
		selectedNotes?: Record<string, string[]>;
	}

	let {
		sessionName = $bindable(""),
		brewingNotes = $bindable(""),
		basics,
		mouthfeel,
		allSelectedNotesList,
		readonly = false,
		class: className = "",
		selectedCategoryIds: propSelectedCategoryIds,
		tastingConversation: propTastingConversation,
		selectedSubCategoryIds: propSelectedSubCategoryIds,
		selectedNotes: propSelectedNotes,
	}: Props = $props();

	// If readonly, we reconstruct the categorized view from the flat allSelectedNotesList
	// This makes using the component in history pages much easier
	const displayData = $derived.by(() => {
		// Use props if provided (Wizard case), otherwise reconstruct (History case)
		if (!readonly && propSelectedCategoryIds && propSelectedNotes && propSelectedSubCategoryIds) {
			return {
				categoryIds: propSelectedCategoryIds,
				notes: propSelectedNotes,
				subCategoryIds: propSelectedSubCategoryIds,
				conversation: propTastingConversation || TASTING_CONVERSATION
			};
		}

		// Reconstruction Logic for History/Readonly mode
		const conversation = propTastingConversation || TASTING_CONVERSATION;
		const categories = [...conversation, ...DEFECT_CONVERSATION];
		const categoryIds: string[] = [];
		const notes: Record<string, string[]> = {};
		const subCategoryIds: Record<string, string[]> = {};

		for (const noteName of allSelectedNotesList) {
			const cat = categories.find(c =>
				c.name === noteName ||
				c.flavors?.some(f => (typeof f === 'string' ? f : f.name) === noteName) ||
				c.subTypes?.some(s => s.name === noteName || s.flavors.some(f => (typeof f === 'string' ? f : f.name) === noteName))
			);

			if (cat) {
				const targetCatId = cat.isDefect ? "defects" : cat.id;
				if (targetCatId !== "defects" && !categoryIds.includes(targetCatId)) {
					categoryIds.push(targetCatId);
				}

				const sub = cat.subTypes?.find(s =>
					s.name === noteName ||
					s.flavors.some(f => (typeof f === 'string' ? f : f.name) === noteName)
				);

				if (sub) {
					if (!subCategoryIds[targetCatId]) subCategoryIds[targetCatId] = [];
					if (!subCategoryIds[targetCatId].includes(sub.id)) {
						subCategoryIds[targetCatId].push(sub.id);
					}

					const isSpecificFlavor = sub.flavors.some(f => (typeof f === 'string' ? f : f.name) === noteName) && noteName !== sub.name;
					if (isSpecificFlavor) {
						if (!notes[targetCatId]) notes[targetCatId] = [];
						if (!notes[targetCatId].includes(noteName)) notes[targetCatId].push(noteName);
					}
				} else {
					const isSpecificFlavor = cat.flavors?.some(f => (typeof f === 'string' ? f : f.name) === noteName) && noteName !== cat.name;
					if (isSpecificFlavor) {
						if (!notes[targetCatId]) notes[targetCatId] = [];
						if (!notes[targetCatId].includes(noteName)) notes[targetCatId].push(noteName);
					}
				}
			} else {
				// Fallback: try the API's note-to-category map (primaryCategory is the category name e.g. "Fruity")
				const apiCategoryName = noteToCategoryMap[noteName.toLowerCase()];
				const apiCat = apiCategoryName
					? conversation.find(c => c.name.toLowerCase() === apiCategoryName.toLowerCase())
					: null;

				if (apiCat) {
					const targetCatId = apiCat.id;
					if (!categoryIds.includes(targetCatId)) categoryIds.push(targetCatId);
					if (!notes[targetCatId]) notes[targetCatId] = [];
					if (!notes[targetCatId].includes(noteName)) notes[targetCatId].push(noteName);
				} else {
					// Last resort: unknown note goes into a catch-all bucket
					if (!notes["other"]) notes["other"] = [];
					if (!notes["other"].includes(noteName)) notes["other"].push(noteName);
					if (!categoryIds.includes("other")) categoryIds.push("other");
				}
			}
		}

		// Ensure "Other" category is in the conversation if needed for display
		const finalConversation = categoryIds.includes("other") && !conversation.some(c => c.id === "other")
			? [...conversation, { id: "other", name: "Other", emoji: "☕", question: "", flavors: [] }]
			: conversation;

		return { categoryIds, notes, subCategoryIds, conversation: finalConversation };
	});
</script>

<Card class={cn("shadow-xl p-8 border-dashed w-full max-w-2xl", className)}>
	<div class="gap-8 grid">
		{#if !readonly}
			<div class="space-y-3">
				<label
					for="session-name"
					class="ml-1 font-bold text-muted-foreground text-xs uppercase tracking-widest"
				>
					Session Name (Optional)
				</label>
				<Input
					id="session-name"
					placeholder="Morning Pour Over, Ethiopia Yirgacheffe, etc."
					bind:value={sessionName}
					class="bg-background shadow-sm h-12 text-lg"
				/>
			</div>

			<div class="space-y-3">
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
					class="bg-background shadow-sm border rounded-md p-3 w-full min-h-[100px] text-lg focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
				></textarea>
			</div>
		{:else}
			{#if brewingNotes}
				<div class="bg-muted/30 p-4 rounded-xl border border-dashed text-sm">
					<p class="mb-1 font-bold text-muted-foreground text-[10px] uppercase tracking-widest">Brewing Notes</p>
					<p class="whitespace-pre-wrap">{brewingNotes}</p>
				</div>
			{/if}
		{/if}

		<!-- Notes -->
		<div class="space-y-6">
			{#each displayData.categoryIds as catId}
				{@const cat = displayData.conversation.find((c) => c.id === catId)}
				{@const subIds = displayData.subCategoryIds[catId] || []}
				{@const specNotes = displayData.notes[catId] || []}
				{#if cat}
					{@const colors = getFlavourCategoryColors(
						cat.name || "Other",
					)}
					<div class="flex flex-col gap-2">
						<div
							class="flex items-center gap-2 font-bold text-muted-foreground text-sm uppercase tracking-widest"
						>
							<span>{cat.emoji}</span>
							{cat.name}
						</div>
						<div class="flex flex-wrap gap-2">
							<!-- Render Subcategories (Only if no specific notes within them were chosen) -->
							{#each subIds as sid}
								{@const sub = cat.subTypes?.find(
									(s) => s.id === sid,
								)}
								{#if sub}
									{@const subFlavorNames = sub.flavors.map(
										(f) =>
											typeof f === "string" ? f : f.name,
									)}
									{@const hasSpecNotesInSub = specNotes.some(
										(n) => subFlavorNames.includes(n),
									)}
									{#if !hasSpecNotesInSub}
										<span
											class={cn(
												"px-3 py-1 border rounded-full font-medium text-sm opacity-80 border-dashed",
												colors.bg,
												colors.text,
												colors.border,
												colors.darkBg,
												colors.darkText,
												colors.darkBorder,
											)}
										>
											{sub.name}
										</span>
									{/if}
								{/if}
							{/each}
 
							<!-- Render Specific Notes -->
							{#each specNotes as note}
								<span
									class={cn(
										"px-3 py-1 border rounded-full font-medium text-sm shadow-sm",
										colors.bg,
										colors.text,
										colors.border,
										colors.darkBg,
										colors.darkText,
										colors.darkBorder,
									)}
								>
									{note}
								</span>
							{/each}
 
							<!-- Render Fallback if no specifics chosen but category is selected -->
							{#if subIds.length === 0 && specNotes.length === 0}
								<span
									class={cn(
										"px-3 py-1 border rounded-full font-medium text-sm border-dashed opacity-70",
										colors.bg,
										colors.text,
										colors.border,
										colors.darkBg,
										colors.darkText,
										colors.darkBorder,
									)}
								>
									{cat.name} (General)
								</span>
							{/if}
						</div>
					</div>
				{/if}
			{/each}
 
			<!-- Render Defects -->
			{#if displayData.notes["defects"] && displayData.notes["defects"].length > 0}
				<div class="flex flex-col gap-2 mt-2 pt-4 border-t">
					<div
						class="flex items-center gap-2 font-bold text-destructive/80 text-sm uppercase tracking-widest"
					>
						<span>⚠️</span> Defects
					</div>
					<div class="flex flex-wrap gap-2">
						{#each displayData.notes["defects"] as note}
							<span
								class="px-3 py-1 border rounded-full font-medium text-sm shadow-sm text-destructive border-destructive/30 bg-destructive/10"
							>
								{note}
							</span>
						{/each}
					</div>
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
					<div
						class="flex justify-between pb-1 border-muted border-b"
					>
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
					<div
						class="flex justify-between pb-1 border-muted border-b"
					>
						<span class="text-muted-foreground"
							>{MOUTHFEEL_QUESTIONS.find((q) => q.id === id)
								?.name}</span
						>
						<span class="font-semibold">{val}</span>
					</div>
				{/each}
			</div>
		</div>
	</div>
</Card>
