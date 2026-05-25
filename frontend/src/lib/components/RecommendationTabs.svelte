<script lang="ts">
	import { Star, Wand2, Citrus, Droplets, Leaf, MapPin, Flame, ChevronDown, Check, Coffee } from "lucide-svelte";
	import { api } from "$lib/api";
	import { getFlavourCategoryColors, formatPrice } from "$lib/utils";
	import * as Card from "$lib/components/ui/card";
	import * as Popover from "$lib/components/ui/popover/index.js";
	import * as Command from "$lib/components/ui/command/index.js";
	import CoffeeBeanImage from "$lib/components/CoffeeBeanImage.svelte";
	import { slide } from "svelte/transition";
	import { untrack } from "svelte";
	import { currencyState } from "$lib/stores/currency.svelte.js";

	interface Props {
		bean: any;
		initialRecommendations: any[];
	}

	let { bean, initialRecommendations } = $props<Props>();

	const profiles = $derived([
		{
			id: "balanced",
			label: "Balanced",
			icon: Star,
			description: "Matches overall character, roast, and origin",
			weights: {
				weight_tasting_notes: 3.0,
				weight_process: 0.5,
				weight_variety: 0.5,
				weight_origin: 1.0,
				weight_roast_level: 1.0,
				weight_different_roaster: 1.0,
				weight_roaster: 0.5
			}
		},
		{
			id: "swapped",
			label: bean.is_decaf ? "Add Caffeine" : "Remove Caffeine",
			icon: Wand2,
			description: bean.is_decaf ? "Find caffeinated versions" : "Find decaf versions",
			weights: {
				weight_tasting_notes: 3.0,
				weight_process: 0,
				weight_variety: 5,
				weight_origin: 1.0,
				weight_roast_level: 0.5,
				weight_different_roaster: 1.0,
				weight_roaster: 0.5
			}
		},
		{
			id: "flavour",
			label: "Flavour",
			icon: Citrus,
			description: "Focuses on matching specific tasting notes",
			weights: {
				weight_tasting_notes: 10.0,
				weight_process: 0.0,
				weight_variety: 0.0,
				weight_origin: 0.0,
				weight_roast_level: 0.5,
				weight_different_roaster: 2.0,
				weight_roaster: 0.0
			}
		},
		{
			id: "process",
			label: "Process",
			icon: Droplets,
			description: "Finds beans with similar processing methods",
			weights: {
				weight_tasting_notes: 1.0,
				weight_process: 8.0,
				weight_variety: 0.0,
				weight_origin: 0.0,
				weight_roast_level: 0.5,
				weight_different_roaster: 1.0,
				weight_roaster: 0.0
			}
		},
		{
			id: "varietal",
			label: "Varietal",
			icon: Leaf,
			description: "Explores the same coffee varieties",
			weights: {
				weight_tasting_notes: 0.5,
				weight_process: 0.0,
				weight_variety: 10.0,
				weight_origin: 0.5,
				weight_roast_level: 1.0,
				weight_different_roaster: 1.0,
				weight_roaster: 0.0
			}
		},
		{
			id: "origin",
			label: "Origin",
			icon: MapPin,
			description: "Grown in the same regions or altitudes",
			weights: {
				weight_tasting_notes: 0.5,
				weight_process: 0.0,
				weight_variety: 0.5,
				weight_origin: 10.0,
				weight_roast_level: 1.0,
				weight_different_roaster: 1.0,
				weight_roaster: 0.0
			}
		},
		{
			id: "roast",
			label: "Roast",
			icon: Flame,
			description: "Matches the roast profile and color",
			weights: {
				weight_tasting_notes: 1.0,
				weight_process: 0.0,
				weight_variety: 0.0,
				weight_origin: 0.5,
				weight_roast_level: 8.0,
				weight_different_roaster: 1.0,
				weight_roaster: 0.0
			}
		},
		{
			id: "roaster",
			label: "Roaster",
			icon: Coffee,
			description: "Other beans from the same roaster",
			weights: {
				weight_tasting_notes: 1.0,
				weight_process: 0.5,
				weight_variety: 0.5,
				weight_origin: 0.5,
				weight_roast_level: 1.0,
				weight_roaster: 100.0,
				weight_different_roaster: 0.0
			}
		}
	]);

	let activeProfileId = $state("balanced");
	let loading = $state(false);
	let recommendations = $state(initialRecommendations);
	let recStates = $state<Record<string, { expanded: boolean }>>({});
	let profileOpen = $state(false);

	const activeProfile = $derived(profiles.find((p) => p.id === activeProfileId)!);

	// Refetch when bean, currency, or profile changes
	$effect(() => {
		const _beanPath = bean.bean_url_path;
		const _currency = currencyState.selectedCurrency;
		const profile = activeProfile;

		untrack(async () => {
			loading = true;
			try {
				recommendations = await api.getDiscoveryRecommendations(
					bean,
					profile.weights,
					_currency || undefined,
					4,
					fetch,
					profile.id === "swapped",
					profile.id === "balanced" && bean.is_decaf
				);
			} catch (error) {
				console.error("Failed to fetch recommendations for profile:", profile.id, error);
				recommendations = [];
			} finally {
				loading = false;
			}
		});
	});

	function toggleExpand(path: string) {
		if (!recStates[path]) recStates[path] = { expanded: false };
		recStates[path].expanded = !recStates[path].expanded;
	}

	function getCommonNotes(recBean: any) {
		const currentNotes = (bean.tasting_notes ?? []).map((n: any) =>
			typeof n === "string" ? n : n.note
		);
		const recNotes = (recBean.tasting_notes ?? []).map((n: any) =>
			typeof n === "string" ? n : n.note
		);
		return recNotes.filter((note: string) => currentNotes.includes(note));
	}
</script>

<Card.Root class="dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:shadow-[0_0_20px_rgba(34,211,238,0.2)] dark:border-cyan-500/30">
	<Card.Header>
		<Card.Title class="flex items-center dark:drop-shadow-[0_0_8px_rgba(16,185,129,0.6)] dark:text-emerald-300">
			<Wand2 class="mr-2 w-5 h-5" />
			Discovery Engine
		</Card.Title>
		<Card.Description>Select a profile to explore similar coffees</Card.Description>
	</Card.Header>
	<Card.Content class="space-y-4">
		<!-- Profile Selector -->
		<div class="flex items-center gap-3">
			<Popover.Root bind:open={profileOpen}>
				<Popover.Trigger
					class="flex justify-between items-center gap-2 bg-background shadow-sm px-3 py-2 border border-input rounded-md focus:outline-none focus:ring-1 focus:ring-ring w-fit min-w-[140px] h-9 text-sm"
					role="combobox"
					aria-expanded={profileOpen}
				>
					<activeProfile.icon class="w-4 h-4 shrink-0" />
					<span class="truncate">{activeProfile.label}</span>
					<ChevronDown class="opacity-50 ml-auto w-4 h-4 shrink-0" />
				</Popover.Trigger>
				<Popover.Content class="p-0 w-[200px]" align="start">
					<Command.Root>
						<Command.List>
							<Command.Group>
								{#each profiles as profile}
									<Command.Item
										value={profile.id}
										onSelect={() => { activeProfileId = profile.id; profileOpen = false; }}
										class="flex items-center gap-2"
									>
										<profile.icon class="w-4 h-4 shrink-0" />
										<div class="flex-1">
											<span class="text-sm">{profile.label}</span>
											<p class="text-[10px] leading-tight">{profile.description}</p>
										</div>
										{#if activeProfileId === profile.id}
											<Check class="ml-auto w-4 h-4 shrink-0" />
										{/if}
									</Command.Item>
								{/each}
							</Command.Group>
						</Command.List>
					</Command.Root>
				</Popover.Content>
			</Popover.Root>
		</div>

		<!-- Recommendations List -->
		<div class="relative space-y-4 min-h-[200px]">
			{#if loading}
				<div class="z-10 absolute inset-0 flex justify-center items-center bg-background/20 backdrop-blur-[1px] transition-opacity">
					<div class="border-primary border-b-2 rounded-full w-8 h-8 animate-spin"></div>
				</div>
			{/if}

			{#if recommendations && recommendations.length > 0}
				<div class="space-y-4">
					{#each recommendations.slice(0, 4) as recBean (recBean.id)}
						<div
							class="flex gap-3 pb-4 last:pb-0 border-b last:border-b-0"
							transition:slide={{ duration: 200 }}
						>
							<div class="flex-shrink-0">
								<CoffeeBeanImage
									bean={recBean}
									size="sm"
									class="shadow-sm rounded-md w-16 h-16"
								/>
							</div>

							<div class="flex-1 space-y-1">
								<div class="flex justify-between items-start">
									<div>
										<a
											href={recBean.bean_url_path ? `/roasters${recBean.bean_url_path}` : "#"}
											class="font-semibold text-sm hover:underline line-clamp-1"
										>
											{recBean.name}
										</a>
										<p class="text-muted-foreground text-xs">{recBean.roaster}, {recBean.roaster_location}</p>
									</div>
									<!-- {#if recBean.score}
										<div class="flex items-center gap-1 bg-primary/10 px-1.5 py-0.5 rounded font-bold text-[10px] text-primary">
											Match: {Math.round(recBean.score)}
										</div>
									{/if} -->
								</div>

								<!-- Shared Notes Highlight -->
								{#if recBean.tasting_notes && recBean.tasting_notes.length > 0}
									<div class="flex flex-wrap gap-1 mt-1">
										{#each (recStates[recBean.bean_url_path]?.expanded ? (typeof recBean.tasting_notes[0] === 'string' ? recBean.tasting_notes : recBean.tasting_notes.map(n => n.note)) : (typeof recBean.tasting_notes[0] === 'string' ? recBean.tasting_notes.slice(0, 2) : recBean.tasting_notes.slice(0, 2).map(n => n.note))) as note (note)}
											{@const matchingNote = (bean.tasting_notes ?? [])
												.map((d) => (typeof d === "string" ? d : d.note))
												.includes(note)}
											{@const flavorNoteObj = recBean.tasting_notes.find(tn => (typeof tn === 'string' ? tn : tn.note) === note)}
											{@const flavorCategory = typeof flavorNoteObj === 'object' ? flavorNoteObj.primary_category : ""}
											{@const categoryColors = getFlavourCategoryColors(flavorCategory)}

											<span
												class="inline-flex items-center {categoryColors.bg} {categoryColors.darkBg} {categoryColors.text} {categoryColors.darkText} px-2 py-0.5 rounded-full text-xs transition-all duration-200 dark:shadow-[0_0_6px_rgba(34,211,238,0.2)]"
												class:border={matchingNote}
												style={matchingNote ? "border-color: rgba(34, 211, 238, 0.5); border-width: 1px;" : ""}
												title={matchingNote ? "Common tasting note" : (flavorCategory ? `Category: ${flavorCategory}` : "")}
											>
												{note}
											</span>
										{/each}
										{#if recBean.tasting_notes.length > 2}
											<button
												class="ml-1 text-[10px] text-muted-foreground hover:underline"
												onclick={() => toggleExpand(recBean.bean_url_path)}
											>
												{recStates[recBean.bean_url_path]?.expanded ? "show less" : `+${recBean.tasting_notes.length - 2}`}
											</button>
										{/if}
									</div>
								{/if}

								<div class="flex justify-between items-center pt-1 text-xs">
									<span class="font-medium">
										{recBean.price ? formatPrice(recBean.price, recBean.currency) : "Price N/A"}
									</span>
									{#if recBean.in_stock}
										<span class="font-semibold text-emerald-600 dark:text-emerald-400">In stock</span>
									{:else}
										<span class="opacity-70 text-red-500">Out of stock</span>
									{/if}
								</div>
							</div>
						</div>
					{/each}
				</div>
			{:else if !loading}
				<div class="flex flex-col justify-center items-center py-8 text-center">
					<p class="text-muted-foreground text-sm">No similar coffees found for this profile.</p>
				</div>
			{/if}
		</div>
	</Card.Content>
</Card.Root>
