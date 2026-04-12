<script lang="ts">
	import { Button } from "$lib/components/ui/button";
	import * as Popover from "$lib/components/ui/popover";
	import * as Command from "$lib/components/ui/command";
	import { cn } from "$lib/utils";
	import { Search, ChevronDown, Check, Plus } from "lucide-svelte";

	interface Props {
		contextualFlavors: string[];
		allSelectedNotesList: string[];
		categoryName: string;
		onAddFlavor: (name: string) => void;
	}

	let {
		contextualFlavors,
		allSelectedNotesList,
		categoryName,
		onAddFlavor,
	}: Props = $props();

	// All state is LOCAL to this component instance —
	// destroyed and recreated cleanly by the parent's {#key} block.
	let searchOpen = $state(false);
	let searchQuery = $state("");

	function handleAdd(name: string) {
		onAddFlavor(name);
		searchOpen = false;
		searchQuery = "";
	}
</script>

<div class="mb-8 w-full max-w-sm mx-auto">
	<Popover.Root bind:open={searchOpen}>
		<Popover.Trigger
			class="flex justify-between items-center bg-background/50 border-input ring-offset-background h-10 w-full rounded-xl border px-4 py-2 text-sm shadow-sm backdrop-blur-sm transition-all duration-300 hover:border-muted-foreground/30 hover:bg-muted/30 focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
			role="combobox"
			aria-expanded={searchOpen}
		>
			<span class="flex items-center gap-2 text-muted-foreground">
				<Search class="size-4" />
				Search or add a flavor...
			</span>
			<ChevronDown class="size-4 shrink-0 opacity-50" />
		</Popover.Trigger>
		<Popover.Content class="w-[300px] p-0" align="start">
			<Command.Root>
				<Command.Input
					placeholder={`Search ${categoryName || "flavor"} notes...`}
					bind:value={searchQuery}
					class="h-10"
				/>
				<Command.List class="no-scrollbar max-h-[300px] overflow-y-auto">
					<Command.Empty>
						{#if searchQuery.length > 1}
							<div class="p-4 text-center">
								<p
									class="text-xs text-muted-foreground mb-3 italic"
								>
									"{searchQuery}" not in {categoryName ||
										"category"} list
								</p>
								<Button
									size="sm"
									class="w-full gap-2"
									onclick={() => handleAdd(searchQuery)}
								>
									<Plus size={14} />
									Add "{searchQuery}"
								</Button>
							</div>
						{:else}
							No results found
						{/if}
					</Command.Empty>
					<Command.Group
						heading={`Standard ${categoryName || ""} Flavors`}
					>
						{#each contextualFlavors as flavor}
							<Command.Item
								value={flavor}
								onSelect={() => handleAdd(flavor)}
								class="flex items-center justify-between"
							>
								<div class="flex items-center gap-2">
									<Check
										class={cn(
											"size-4",
											!allSelectedNotesList.includes(
												flavor,
											) && "text-transparent",
										)}
									/>
									{flavor}
								</div>
							</Command.Item>
						{/each}
					</Command.Group>
				</Command.List>
			</Command.Root>
		</Popover.Content>
	</Popover.Root>
</div>
