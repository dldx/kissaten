<script lang="ts">
	import {
		TASTING_CONVERSATION,
		DEFECT_CONVERSATION,
		MOUTHFEEL_QUESTIONS,
		TASTE_BASICS_QUESTIONS,
		type TastingConversationCategory,
	} from "$lib/tasting/conversation";
	import CategoryTile from "./CategoryTile.svelte";
	import FlavorChip from "./FlavorChip.svelte";
	import FlavorSearchCombobox from "./FlavorSearchCombobox.svelte";
	import TastingSummaryCard from "./TastingSummaryCard.svelte";
	import WizardProgress from "./WizardProgress.svelte";
	import { Button } from "$lib/components/ui/button";
	import { cn, getFlavourCategoryColors } from "$lib/utils";
	import {
		ChevronLeft,
		ChevronRight,
		Search,
		ClipboardList,
		RotateCcw,
		Save,
	} from "lucide-svelte";
	import { fade, fly } from "svelte/transition";
	import { db } from "$lib/db/localdb";
	import { toast } from "svelte-sonner";
	import { onMount } from "svelte";
	import { api } from "$lib/api";
	import { mergeDynamicFlavours } from "$lib/tasting/conversation";
	import { pushState, replaceState } from "$app/navigation";
	import { page } from "$app/state";
	import { tick } from "svelte";

	// --- State ---
	type Step =
		| "basics"
		| "overview"
		| "category"
		| "subcategory"
		| "subcategory_picker"
		| "mouthfeel"
		| "defects"
		| "summary";

	let currentStep = $state<Step>("basics");
	let categoryIndex = $state(0);
	let subCategoryIndex = $state(0);
	let currentSessionId = $state<number | null>(null);

	// Sync state from history (browser back/forward)
	$effect(() => {
		if (page.state && (page.state as any).currentStep) {
			const s = page.state as any;
			currentStep = s.currentStep;
			categoryIndex = s.categoryIndex ?? 0;
			subCategoryIndex = s.subCategoryIndex ?? 0;
		} else if (currentStep !== "basics") {
			// Back to initial entry
			currentStep = "basics";
			categoryIndex = 0;
			subCategoryIndex = 0;
		}
	});

	// Dedicated effect for scrolling to top on any meaningful step change
	$effect(() => {
		// Track dependencies
		currentStep;
		categoryIndex;
		subCategoryIndex;

		// We use tick() to wait for Svelte to update the DOM, then scroll.
		// Using 'instant' often avoids conflicts with FLIP/View transitions.
		tick().then(() => {
			window.scrollTo({ top: 0, behavior: "instant" });
		});
	});

	function updateHistory(method: "push" | "replace" = "push") {
		const s = { currentStep, categoryIndex, subCategoryIndex };
		if (method === "push") {
			pushState("", s);
		} else {
			replaceState("", s);
		}
	}
	let selectedSubCategoryIds = $state<Record<string, string[]>>({}); // Track which sub-categories are chosen for each main cat

	// Selections
	let sessionName = $state("");
	let brewingNotes = $state("");
	let selectedCategoryIds = $state<string[]>([]);
	let selectedNotes = $state<Record<string, string[]>>({});
	let mouthfeel = $state<Record<string, string>>({});
	let basics = $state<Record<string, string>>({});
	let isDefectsExpanded = $state(false);
	let isFetchingFlavours = $state(false);
	let noteSubIdMap = $state<Record<string, string>>({}); // Tracks which sub-category a custom note was added in


	let wizardContainer = $state<HTMLDivElement>(null!);

	// Dynamic Data
	let tastingConversation = $state(TASTING_CONVERSATION);

	// Computed
	const currentCategory = $derived.by(() => {
		if (
			selectedCategoryIds.length > 0 &&
			(currentStep === "category" ||
				currentStep === "subcategory" ||
				currentStep === "subcategory_picker")
		) {
			const cat = tastingConversation.find(
				(c) => c.id === selectedCategoryIds[categoryIndex],
			);
			return cat || null;
		}
		// In defects step, we don't have a 'current' category in the same way,
		// but for the search box we can return a pseudo-category or the first defect group
		// if we want to keep the current logic, but it's better to handle it in contextualFlavors.
		if (currentStep === "defects") {
			return { id: "defects", name: "Defects", flavors: [] } as any;
		}
		return null;
	});

	const activeSubCategories = $derived.by(() => {
		if (!currentCategory?.subTypes) return [];
		const selectedIds = selectedSubCategoryIds[currentCategory.id] || [];
		return currentCategory.subTypes.filter((s: any) =>
			selectedIds.includes(s.id),
		);
	});

	const currentSubCategory = $derived(
		activeSubCategories.length > 0 && currentStep === "subcategory"
			? activeSubCategories[subCategoryIndex]
			: null,
	);

	const contextualFlavors = $derived.by(() => {
		// Priority 0: Defects step (search all defects)
		if (currentStep === "defects") {
			const f = new Set<string>();
			DEFECT_CONVERSATION.forEach((cat) => {
				(cat.flavors || []).forEach((n: any) =>
					f.add(typeof n === "string" ? n : n.name),
				);
			});
			return Array.from(f).sort();
		}

		// Priority 1: Current sub-category (if we are in a detail step)
		if (currentSubCategory) {
			const f = new Set<string>();
			(currentSubCategory.flavors || []).forEach((n: any) =>
				f.add(typeof n === "string" ? n : n.name),
			);
			return Array.from(f).sort();
		}

		// Priority 2: Primary category (including all sub-types)
		if (!currentCategory) return [];
		const f = new Set<string>();
		(currentCategory.flavors || []).forEach((n: any) =>
			f.add(typeof n === "string" ? n : n.name),
		);
		(currentCategory.subTypes || []).forEach((sub: any) => {
			(sub.flavors || []).forEach((n: any) =>
				f.add(typeof n === "string" ? n : n.name),
			);
		});
		return Array.from(f).sort();
	});



	onMount(() => {
		window.addEventListener("keydown", handleKeydown);

		// Async fetch
		(async () => {
			isFetchingFlavours = true;
			// Initialize history state if not present (delayed to avoid router initialization issues)
			setTimeout(() => {
				if (!page.state || !(page.state as any).currentStep) {
					updateHistory("replace");
				}
			}, 0);

			console.log("Fetching dynamic flavours...");
			try {
				const response = await api.getTastingNoteCategories();
				console.log("API Response for flavours:", response);
				if (response.success && response.data) {
					const merged = mergeDynamicFlavours(
						TASTING_CONVERSATION,
						response.data.categories,
					);
					console.log("Merged conversation:", merged);
					tastingConversation = merged;
				}
			} catch (e) {
				console.error("Failed to fetch dynamic flavours:", e);
			} finally {
				isFetchingFlavours = false;
			}
		})();

		return () => window.removeEventListener("keydown", handleKeydown);
	});

	const progressStepCount = $derived.by(() => {
		let total = 2; // Basics + Overview
		for (const catId of selectedCategoryIds) {
			const cat = tastingConversation.find((c) => c.id === catId);
			if (cat?.subTypes) {
				const activeCount = selectedSubCategoryIds[catId]?.length || 0;
				total += 1; // The picker step
				total += activeCount;
			} else {
				total += 1;
			}
		}
		total += 1; // Mouthfeel (Finish)
		total += 1; // Defects overview
		return total;
	});

	const currentProgressIndex = $derived.by(() => {
		if (currentStep === "basics") return 0;
		if (currentStep === "overview") return 1;
		if (
			currentStep === "category" ||
			currentStep === "subcategory" ||
			currentStep === "subcategory_picker"
		) {
			let index = 2;
			for (let i = 0; i < categoryIndex; i++) {
				const catId = selectedCategoryIds[i];
				const cat = tastingConversation.find((c) => c.id === catId);
				if (cat?.subTypes) {
					index += 1; // Picker
					index += selectedSubCategoryIds[catId]?.length || 0;
				} else {
					index += 1;
				}
			}
			if (currentStep === "subcategory_picker") return index;
			if (currentStep === "subcategory")
				return index + 1 + subCategoryIndex;
			return index; // "category" case
		}
		if (currentStep === "mouthfeel") return progressStepCount - 2;
		if (currentStep === "defects") return progressStepCount - 1;
		return progressStepCount - 1;
	});

	const allSelectedNotesList = $derived.by(() => {
		const notes = new Set<string>();

		// 1. Add all specific flavors (most specific level)
		const allSpecificFlavors = Object.values(selectedNotes).flat();
		allSpecificFlavors.forEach((n) => notes.add(n));

		// 2. Add categories or sub-categories only if no more specific child is selected
		selectedCategoryIds.forEach((catId) => {
			const cat = [...tastingConversation, ...DEFECT_CONVERSATION].find(
				(c) => c.id === catId,
			);
			if (!cat) return;

			const specificNotesInThisCat = selectedNotes[catId] || [];

			if (cat.subTypes) {
				const selectedSubIds = selectedSubCategoryIds[catId] || [];

				// Handle Sub-categories
				selectedSubIds.forEach((sid) => {
					const sub = cat.subTypes?.find((s) => s.id === sid);
					if (!sub) return;

					// Check if any specific flavors from this sub-category were picked
					const subFlavorNames = sub.flavors.map((f) =>
						typeof f === "string" ? f : f.name,
					);
					const hasSpecificsInSub = specificNotesInThisCat.some((n) =>
						subFlavorNames.includes(n),
					);

					// If no specific flavors from this sub-group picked, record the sub-group name
					if (!hasSpecificsInSub) {
						notes.add(sub.name);
					}
				});

				// Handle Primary Category: Only add if absolutely nothing else was picked in it
				if (
					selectedSubIds.length === 0 &&
					specificNotesInThisCat.length === 0
				) {
					notes.add(cat.name);
				}
			} else {
				// No sub-categories (like "Sweet" or "Floral")
				// Only add category name ("Sweet") if no specific notes (like "Honey") were picked
				if (specificNotesInThisCat.length === 0) {
					notes.add(cat.name);
				}
			}
		});

		return Array.from(notes);
	});

	// --- Actions ---
	function next() {
		if (currentStep === "basics") {
			currentStep = "overview";
		} else if (currentStep === "overview") {
			if (selectedCategoryIds.length > 0) {
				categoryIndex = 0;
				moveToCategory(0);
			} else {
				currentStep = "mouthfeel";
			}
		} else if (currentStep === "subcategory_picker") {
			const catId = selectedCategoryIds[categoryIndex];
			const activeCount = selectedSubCategoryIds[catId]?.length || 0;
			if (activeCount > 0) {
				subCategoryIndex = 0;
				currentStep = "subcategory";
			} else if (categoryIndex < selectedCategoryIds.length - 1) {
				categoryIndex++;
				moveToCategory(categoryIndex);
			} else {
				currentStep = "mouthfeel";
			}
		} else if (
			currentStep === "category" ||
			currentStep === "subcategory"
		) {
			const cat = currentCategory;
			const activeCount = cat?.id
				? selectedSubCategoryIds[cat.id]?.length || 0
				: 0;

			if (
				currentStep === "subcategory" &&
				subCategoryIndex < activeCount - 1
			) {
				subCategoryIndex++;
				currentStep = "subcategory";
			} else if (categoryIndex < selectedCategoryIds.length - 1) {
				categoryIndex++;
				moveToCategory(categoryIndex);
			} else {
				currentStep = "mouthfeel";
			}
		} else if (currentStep === "mouthfeel") {
			currentStep = "defects";
		} else if (currentStep === "defects") {
			currentStep = "summary";
		}

		updateHistory("push");
	}

	function back() {
		if (currentStep !== "basics") {
			history.back();
		}
	}

	function moveToCategory(idx: number) {
		const cat = tastingConversation.find(
			(c) => c.id === selectedCategoryIds[idx],
		);
		if (cat?.subTypes) {
			currentStep = "subcategory_picker";
		} else {
			currentStep = "category";
		}
	}

	function toggleCategory(id: string) {
		if (selectedCategoryIds.includes(id)) {
			selectedCategoryIds = selectedCategoryIds.filter((i) => i !== id);
			delete selectedNotes[id];
			delete selectedSubCategoryIds[id];
		} else {
			selectedCategoryIds = [...selectedCategoryIds, id];
		}
	}

	function toggleSubCategory(catId: string, subId: string) {
		const current = selectedSubCategoryIds[catId] || [];
		if (current.includes(subId)) {
			selectedSubCategoryIds[catId] = current.filter(
				(id) => id !== subId,
			);
			// Clean up notes for flavors that are in this subcategory but no longer selected
			const sub = tastingConversation
				.find((c) => c.id === catId)
				?.subTypes?.find((s) => s.id === subId);
			if (sub && selectedNotes[catId]) {
				selectedNotes[catId] = selectedNotes[catId].filter(
					(n) => !sub.flavors.includes(n),
				);
			}
		} else {
			selectedSubCategoryIds[catId] = [...current, subId];
		}
	}

	function toggleNote(categoryId: string | undefined, note: string) {
		if (!categoryId) return;
		const current = selectedNotes[categoryId] || [];
		if (current.includes(note)) {
			selectedNotes[categoryId] = current.filter((n) => n !== note);
		} else {
			selectedNotes[categoryId] = [...current, note];
		}
	}

	function findSubCategoryForFlavor(
		name: string,
		category: TastingConversationCategory,
	) {
		if (!category.subTypes) return null;
		for (const sub of category.subTypes) {
			if (
				sub.flavors.some(
					(f) => (typeof f === "string" ? f : f.name) === name,
				)
			)
				return sub.id;
		}
		return null;
	}

	function addFlavor(name: string) {
		if (!name || !currentCategory) return;

		const catId = currentCategory.id;
		const subId =
			currentStep === "defects"
				? null
				: findSubCategoryForFlavor(name, currentCategory) ||
					currentSubCategory?.id;

		toggleNote(catId, name);

		if (subId) {
			noteSubIdMap[name] = subId;
		}

		// Ensure category is selected
		const isDefect = currentStep === "defects" || currentCategory.isDefect;
		if (
			!isDefect &&
			catId !== "other" &&
			!selectedCategoryIds.includes(catId)
		) {
			selectedCategoryIds = [...selectedCategoryIds, catId];
		}

	}

	async function saveTasting() {
		try {
			// Convert $state objects to plain JS objects to avoid Dexie/IndexedDB cloning issues
			const session: any = {
				date: new Date(),
				name: sessionName.trim() || undefined,
				brewingNotes: brewingNotes.trim() || undefined,
				selectedNotes: $state.snapshot(allSelectedNotesList),
				mouthfeel: $state.snapshot(mouthfeel),
				basics: $state.snapshot(basics),
			};

			if (currentSessionId) {
				session.id = currentSessionId;
			}

			console.log("Saving tasting session:", session);
			const id = await db.tastings.put(session);
			const isUpdate = !!currentSessionId;
			currentSessionId = id as number;
			toast.success(
				isUpdate
					? "Tasting session updated!"
					: "Tasting session saved!",
			);
		} catch (e) {
			console.error("Failed to save tasting", e);
			toast.error("Failed to save session");
		}
	}

	function reset() {
		currentStep = "basics";
		categoryIndex = 0;
		subCategoryIndex = 0;
		currentSessionId = null;
		selectedSubCategoryIds = {};
		sessionName = "";
		brewingNotes = "";
		selectedCategoryIds = [];
		selectedNotes = {};
		mouthfeel = {};
		basics = {};
		isDefectsExpanded = false;

		updateHistory("push");
	}

	function getSearchUrl() {
		const params = new URLSearchParams();
		if (allSelectedNotesList.length > 0) {
			// Join with '&' to create a boolean 'AND' search in the backend
			params.set("tasting_notes_query", allSelectedNotesList.join("&"));
		}
		return `/search?${params.toString()}`;
	}

	// --- Keyboard Navigation ---
	function handleKeydown(e: KeyboardEvent) {
		// Ignore if focused on an input (including the search combobox)
		if (
			document.activeElement?.tagName === "INPUT" ||
			document.activeElement?.tagName === "TEXTAREA" ||
			document.activeElement?.getAttribute("role") === "combobox"
		) {
			return;
		}

		if (e.key === "Enter" || e.key === "ArrowRight") {
			next();
		} else if (e.key === "ArrowLeft" || e.key === "Backspace") {
			back();
		} else if (/^[1-9]$/.test(e.key)) {
			const idx = parseInt(e.key) - 1;
			if (currentStep === "basics" || currentStep === "mouthfeel") {
				const questions =
					currentStep === "basics"
						? TASTE_BASICS_QUESTIONS
						: MOUTHFEEL_QUESTIONS;
				const state = currentStep === "basics" ? basics : mouthfeel;

				const activeQ = questions.find((q, i) => {
					const isCompleted = state[q.id];
					const isPreviousCompleted =
						i === 0 || state[questions[i - 1].id];
					return isPreviousCompleted && !isCompleted;
				});

				if (activeQ && activeQ.options[idx]) {
					selectOption(
						activeQ.id,
						activeQ.options[idx],
						currentStep as any,
					);
				}
			}
		}
	}

	function selectOption(
		qId: string,
		opt: string,
		step: "basics" | "mouthfeel",
	) {
		console.log(`[TastingWizard] selectOption: ${step} - ${qId} = ${opt}`);
		const questions =
			step === "basics" ? TASTE_BASICS_QUESTIONS : MOUTHFEEL_QUESTIONS;
		const currentIdx = questions.findIndex((q) => q.id === qId);

		if (step === "basics") {
			basics[qId] = opt;
		} else {
			mouthfeel[qId] = opt;
		}

		if (currentIdx === questions.length - 1) {
			console.log(
				`[TastingWizard] Last question of ${step}, advancing...`,
			);
			setTimeout(next, 300);
		} else {
			const nextQ = questions[currentIdx + 1];
			console.log(`[TastingWizard] Scrolling to next: q-${nextQ.id}`);
			// Small delay to ensure DOM and transitions have started
			setTimeout(() => {
				const el = document.getElementById(`q-${nextQ.id}`);
				if (el) {
					el.scrollIntoView({
						behavior: "smooth",
						block: "center",
					});
				} else {
					console.warn(
						`[TastingWizard] Could not find element q-${nextQ.id}`,
					);
				}
			}, 60);
		}
	}
</script>

<div
	bind:this={wizardContainer}
	class="flex flex-col items-center mx-auto py-6 w-full max-w-4xl min-h-150"
>
	<!-- Header Links -->
	<div class="flex justify-end mb-4 px-4 w-full">
		<Button variant="ghost" size="sm" class="gap-2" href="/tasting/history">
			<ClipboardList size={16} />
			View Past Sessions
		</Button>
	</div>

	<!-- Progress -->
	<div class="mb-12">
		<WizardProgress
			steps={progressStepCount}
			current={currentProgressIndex}
			currentIcon={currentCategory?.emoji ||
				(currentStep === "basics"
					? "👅"
					: currentStep === "overview"
						? "☕"
						: currentStep === "mouthfeel"
							? "👅"
							: "✨")}
		/>
	</div>

	<!-- Content -->
	<div class="flex flex-col justify-center items-center px-4 w-full grow">
		{#key currentStep + (currentStep === "category" ? categoryIndex : "") + (currentStep === "subcategory" ? subCategoryIndex : "")}
			<div
				in:fly={{ x: 20, duration: 400, delay: 100 }}
				out:fade={{ duration: 200 }}
				class="flex flex-col items-center w-full h-full text-center"
			>
				{#if currentStep === "basics"}
					<div class="mb-8 w-full">
						<h1 class="mb-3 font-bold text-3xl">Taste Basics</h1>
						<p class="text-muted-foreground">
							Focus on the foundation of the flavour
						</p>
					</div>
					<div class="gap-12 grid mx-auto pb-12 w-full max-w-sm">
						{#each TASTE_BASICS_QUESTIONS as q, i}
							{@const isCompleted = basics[q.id]}
							{@const isPreviousCompleted =
								i === 0 ||
								basics[TASTE_BASICS_QUESTIONS[i - 1].id]}
							{@const isFocused =
								isPreviousCompleted && !isCompleted}
							<div
								id="q-{q.id}"
								class={cn(
									"flex flex-col gap-4 transition-all duration-500",
									!isPreviousCompleted
										? "opacity-20 pointer-events-none grayscale blur-[1px]"
										: "opacity-100",
									isFocused ? "scale-105" : "scale-100",
								)}
							>
								<div class="flex flex-col gap-1 text-center">
									<p
										class={cn(
											"font-bold text-xs uppercase tracking-[0.2em] transition-colors duration-500",
											isFocused
												? "text-primary"
												: "text-muted-foreground",
										)}
									>
										{q.name}
									</p>
									{#if q.description}
										<p
											class="mx-auto max-w-[280px] text-[10px] text-muted-foreground/60 italic leading-tight"
										>
											{q.description}
										</p>
									{/if}
								</div>
								<div
									class="flex flex-wrap justify-center gap-2"
								>
									{#each q.options as opt}
										<Button
											variant={basics[q.id] === opt
												? "default"
												: "outline"}
											size="lg"
											class={cn(
												"min-w-20 h-14 transition-all duration-300 grow",
											)}
											onclick={() =>
												selectOption(
													q.id,
													opt,
													"basics",
												)}
										>
											{opt}
										</Button>
									{/each}
								</div>
							</div>
						{/each}
					</div>
				{:else if currentStep === "overview"}
					<div class="mb-8 text-center">
						<h1 class="mb-3 font-bold text-3xl">
							Primary Character
						</h1>
						<p class="text-muted-foreground">
							Which broad categories stand out first?
						</p>
					</div>
					<div
						class="gap-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 w-full"
					>
						{#each tastingConversation as cat}
							<CategoryTile
								name={cat.name}
								emoji={cat.emoji}
								selected={selectedCategoryIds.includes(cat.id)}
								onSelect={() => toggleCategory(cat.id)}
							/>
						{/each}
					</div>
				{:else if currentStep === "subcategory_picker" && currentCategory}
					{@const colors = getFlavourCategoryColors(
						currentCategory.name,
					)}
					<div class="mb-10 text-center">
						<div
							class={cn(
								"inline-flex items-center gap-2 mb-4 px-3 py-1 border rounded-full font-bold text-xs uppercase tracking-tighter",
								colors.bg,
								colors.text,
								colors.border,
								colors.darkBg,
								colors.darkText,
								colors.darkBorder,
							)}
						>
							{currentCategory.emoji}
							{currentCategory.name}
						</div>
						<h2
							class="mb-2 font-extrabold text-4xl sm:text-5xl tracking-tight"
						>
							{currentCategory.subTypeQuestion ||
								currentCategory.question}
						</h2>
						<p class="text-muted-foreground italic">
							Select the general families you notice
						</p>
					</div>

					<div
						class="gap-4 grid grid-cols-2 sm:grid-cols-3 px-4 w-full max-w-2xl"
					>
						{#each currentCategory.subTypes || [] as sub}
							<CategoryTile
								name={sub.name}
								emoji={sub.emoji}
								selected={(
									selectedSubCategoryIds[
										currentCategory.id
									] || []
								).includes(sub.id)}
								onSelect={() =>
									toggleSubCategory(
										currentCategory.id,
										sub.id,
									)}
							/>
						{/each}
					</div>
				{:else if currentStep === "category" && currentCategory}
					{@const colors = getFlavourCategoryColors(
						currentCategory.name,
					)}
					<div class="mb-10 text-center">
						<div
							class={cn(
								"inline-flex items-center gap-2 mb-4 px-3 py-1 border rounded-full font-bold text-xs uppercase tracking-tighter",
								colors.bg,
								colors.text,
								colors.border,
								colors.darkBg,
								colors.darkText,
								colors.darkBorder,
							)}
						>
							{currentCategory.emoji}
							{currentCategory.name}
						</div>
						<h2
							class="mb-2 font-extrabold text-4xl sm:text-5xl tracking-tight"
						>
							{currentCategory.question}
						</h2>
					</div>

					<FlavorSearchCombobox
						{contextualFlavors}
						{allSelectedNotesList}
						categoryName={(currentSubCategory || currentCategory)?.name || ""}
						onAddFlavor={addFlavor}
					/>

					<div class="w-full">
						<div
							class="flex flex-wrap justify-center gap-3 mx-auto max-w-2xl relative"
						>
							{#if isFetchingFlavours}
								<div
									class="absolute -top-8 left-1/2 -translate-x-1/2 text-[10px] text-muted-foreground animate-pulse uppercase tracking-widest font-bold"
								>
									Updating counts...
								</div>
							{/if}

							{#each currentCategory?.flavors || [] as flavor, i}
								{@const fName =
									typeof flavor === "string"
										? flavor
										: flavor.name}
								{@const fCount =
									typeof flavor === "string"
										? undefined
										: flavor.count}
								{@const isSelected = (
									currentCategory?.id
										? selectedNotes[currentCategory.id]
										: []
								)?.includes(fName)}
								{#if i < 10 || isSelected}
									<FlavorChip
										name={fName}
										count={fCount}
										categoryName={currentCategory?.name ||
											""}
										selected={isSelected}
										onSelect={() => {
											if (currentCategory?.id) {
												toggleNote(
													currentCategory.id,
													fName,
												);
											}
										}}
										className={isFetchingFlavours
											? "opacity-70"
											: ""}
									/>
								{/if}
							{/each}

							{#each (currentCategory?.id ? selectedNotes[currentCategory.id] : []) || [] as note}
								{#if !contextualFlavors.includes(note) && (!noteSubIdMap[note] || noteSubIdMap[note] === currentSubCategory?.id)}
									<FlavorChip
										name={note}
										categoryName={currentCategory?.name ||
											""}
										selected={true}
										onSelect={() => {
											if (currentCategory?.id) {
												toggleNote(
													currentCategory.id,
													note,
												);
											}
										}}
									/>
								{/if}
							{/each}
						</div>
					</div>
				{:else if currentStep === "subcategory" && currentCategory && currentSubCategory}
					{@const colors = getFlavourCategoryColors(
						currentCategory.name,
					)}
					<div class="mb-10 text-center">
						<div
							class={cn(
								"inline-flex items-center gap-2 mb-4 px-3 py-1 border rounded-full font-bold text-xs uppercase tracking-tighter",
								colors.bg,
								colors.text,
								colors.border,
								colors.darkBg,
								colors.darkText,
								colors.darkBorder,
							)}
						>
							{currentCategory?.emoji}
							{currentCategory?.name} / {currentSubCategory?.emoji}
							{currentSubCategory?.name}
						</div>
						<h2
							class="mb-2 font-extrabold text-4xl sm:text-5xl tracking-tight"
						>
							Detail the {currentSubCategory?.name || ""} notes
						</h2>
						<p class="text-muted-foreground">
							Picking specific {(
								currentSubCategory?.name || ""
							).toLowerCase()}
							flavours
						</p>
					</div>

					<FlavorSearchCombobox
						{contextualFlavors}
						{allSelectedNotesList}
						categoryName={(currentSubCategory || currentCategory)?.name || ""}
						onAddFlavor={addFlavor}
					/>

					<div class="w-full">
						<div
							class="flex flex-wrap justify-center gap-3 mx-auto max-w-2xl"
						>
							{#each currentSubCategory.flavors as flavor, i}
								{@const fName =
									typeof flavor === "string"
										? flavor
										: flavor.name}
								{@const fCount =
									typeof flavor === "string"
										? undefined
										: flavor.count}
								{@const isSelected = (
									currentCategory?.id
										? selectedNotes[currentCategory.id]
										: []
								)?.includes(fName)}
								{#if i < 10 || isSelected}
									<FlavorChip
										name={fName}
										count={fCount}
										categoryName={currentCategory?.name ||
											""}
										selected={isSelected}
										onSelect={() => {
											if (currentCategory?.id) {
												toggleNote(
													currentCategory.id,
													fName,
												);
											}
										}}
									/>
								{/if}
							{/each}

							{#each (currentCategory?.id ? selectedNotes[currentCategory.id] : []) || [] as note}
								{#if !contextualFlavors.includes(note) && (!noteSubIdMap[note] || noteSubIdMap[note] === currentSubCategory?.id)}
									<FlavorChip
										name={note}
										categoryName={currentCategory?.name ||
											""}
										selected={true}
										onSelect={() => {
											if (currentCategory?.id) {
												toggleNote(
													currentCategory.id,
													note,
												);
											}
										}}
									/>
								{/if}
							{/each}
						</div>
					</div>
				{:else if currentStep === "mouthfeel"}
					<div class="mb-8 w-full">
						<h1 class="mb-3 font-bold text-3xl">
							Mouthfeel & Finish
						</h1>
						<p class="text-muted-foreground">
							Describe the physical sensations
						</p>
					</div>
					<div class="gap-12 grid mx-auto pb-12 w-full max-w-sm">
						{#each MOUTHFEEL_QUESTIONS as q, i}
							{@const isCompleted = mouthfeel[q.id]}
							{@const isPreviousCompleted =
								i === 0 ||
								mouthfeel[MOUTHFEEL_QUESTIONS[i - 1].id]}
							{@const isFocused =
								isPreviousCompleted && !isCompleted}
							<div
								id="q-{q.id}"
								class={cn(
									"flex flex-col gap-4 transition-all duration-500",
									!isPreviousCompleted
										? "opacity-20 pointer-events-none grayscale blur-[1px]"
										: "opacity-100",
									isFocused ? "scale-105" : "scale-100",
								)}
							>
								<div class="flex flex-col gap-1 text-center">
									<p
										class={cn(
											"font-bold text-xs uppercase tracking-[0.2em] transition-colors duration-500",
											isFocused
												? "text-primary"
												: "text-muted-foreground",
										)}
									>
										{q.name}
									</p>
									{#if q.description}
										<p
											class="mx-auto max-w-[280px] text-[10px] text-muted-foreground/60 italic leading-tight"
										>
											{q.description}
										</p>
									{/if}
								</div>
								<div
									class="flex flex-wrap justify-center gap-2"
								>
									{#each q.options as opt}
										<Button
											variant={mouthfeel[q.id] === opt
												? "default"
												: "outline"}
											size="lg"
											class={cn(
												"min-w-28 h-14 transition-all duration-300 grow",
											)}
											onclick={() =>
												selectOption(
													q.id,
													opt,
													"mouthfeel",
												)}
										>
											{opt}
										</Button>
									{/each}
								</div>
							</div>
						{/each}
					</div>
				{:else if currentStep === "defects"}
					<div class="mb-10 text-center">
						<div
							class="inline-flex items-center gap-2 bg-destructive/10 dark:bg-destructive/20 mb-4 px-3 py-1 border border-destuctive/20 rounded-full font-bold text-destructive text-xs uppercase tracking-tighter"
						>
							⚠️ Potential Defects
						</div>
						<h2
							class="mb-2 font-extrabold text-4xl sm:text-5xl tracking-tight"
						>
							Any off-flavours?
						</h2>
						<p class="text-muted-foreground">
							Select if you notice any process or storage taints
						</p>
					</div>

					<FlavorSearchCombobox
						{contextualFlavors}
						{allSelectedNotesList}
						categoryName={(currentSubCategory || currentCategory)?.name || "Defects"}
						onAddFlavor={addFlavor}
					/>

					<div class="space-y-10 mx-auto w-full max-w-2xl">
						{#each DEFECT_CONVERSATION as def}
							<div class="flex flex-col gap-4">
								<p
									class="flex items-center gap-2 font-semibold text-destructive/80 text-sm uppercase tracking-wide"
								>
									<span>{def.emoji}</span>
									{def.name}
								</p>
								<div class="flex flex-wrap gap-2">
									{#each def.flavors as flavor}
										{@const fName =
											typeof flavor === "string"
												? flavor
												: flavor.name}
										{@const fCount =
											typeof flavor === "string"
												? undefined
												: flavor.count}
										<FlavorChip
											name={fName}
											count={fCount}
											categoryName="Other"
											selected={selectedNotes[
												"defects"
											]?.includes(fName)}
											onSelect={() =>
												toggleNote("defects", fName)}
										/>
									{/each}
								</div>
							</div>
						{/each}
					</div>
				{:else if currentStep === "summary"}
					<div class="mb-8 text-center">
						<h1 class="mb-2 font-black text-4xl tracking-tighter">
							Tasting Session Summary
						</h1>
						<p class="text-muted-foreground">
							Name your session and save your profile
						</p>
					</div>

					<TastingSummaryCard
						bind:sessionName
						bind:brewingNotes
						{selectedCategoryIds}
						{tastingConversation}
						{selectedSubCategoryIds}
						{selectedNotes}
						{basics}
						{mouthfeel}
						{allSelectedNotesList}
					/>

					<div
						class="flex flex-wrap justify-center gap-4 mt-12 w-full"
					>
						<Button
							size="lg"
							class="gap-4 shadow-lg hover:shadow-xl px-10 transition-all"
							onclick={saveTasting}
						>
							<Save size={20} />
							Save Session
						</Button>

						<div class="flex justify-center gap-3 w-full">
							<Button
								size="sm"
								variant="outline"
								class="gap-2"
								href={getSearchUrl()}
							>
								<Search size={16} />
								Find matching beans
							</Button>
							<Button
								size="sm"
								variant="outline"
								class="gap-2"
								onclick={() => {
									const text = `Kissaten Coffee Tasting\n\nNotes: ${allSelectedNotesList.join(", ")}\n\nBasics: ${Object.entries(
										basics,
									)
										.map(([k, v]) => `${k}:${v}`)
										.join(
											", ",
										)}${brewingNotes ? `\n\nBrewing Notes: ${brewingNotes}` : ""}`;
									navigator.clipboard.writeText(text);
									toast.success(
										"Summary copied to clipboard!",
									);
								}}
							>
								<ClipboardList size={16} />
								Copy Results
							</Button>
							<Button
								size="sm"
								variant="ghost"
								class="gap-2"
								onclick={reset}
							>
								<RotateCcw size={16} />
								Start Over
							</Button>
						</div>
					</div>
				{/if}
			</div>
		{/key}
	</div>

	<!-- Navigation Footer -->
	{#if currentStep !== "summary"}
		<div
			class="bottom-0 sticky flex justify-between items-center bg-background/95 mt-12 px-4 py-6 border-t w-full z-10 backdrop-blur-sm shadow-[0_-1px_3px_rgba(0,0,0,0.05)]"
		>
			<Button
				variant="ghost"
				onclick={back}
				disabled={currentStep === "basics"}
				class="gap-2"
			>
				<ChevronLeft size={18} />
				Back
			</Button>

			<Button onclick={next} class="gap-2 min-w-30">
				{currentStep === "defects" ? "Finish" : "Next"}
				<ChevronRight size={18} />
			</Button>
		</div>
	{/if}
</div>



<style>
	/* Any additional specific animation styles can go here */
</style>
