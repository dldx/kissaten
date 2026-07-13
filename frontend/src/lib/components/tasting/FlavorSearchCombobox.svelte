<script lang="ts">
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
		onAddFlavor(name.trim());
		searchOpen = false;
		searchQuery = "";
	}
</script>

<div class="mx-auto mb-8 w-full max-w-sm">
	<Popover.Root bind:open={searchOpen}>
		<Popover.Trigger
			class="flex justify-between items-center bg-background/50 hover:bg-muted/30 disabled:opacity-50 shadow-sm backdrop-blur-sm px-4 py-2 border border-input hover:border-muted-foreground/30 rounded-xl focus:outline-none focus:ring-1 focus:ring-ring ring-offset-background w-full h-10 text-sm transition-all duration-300 disabled:cursor-not-allowed"
			role="combobox"
			aria-expanded={searchOpen}
		>
			<span class="flex items-center gap-2 text-muted-foreground">
				<Search class="size-4" />
				Search or add a flavor...
			</span>
			<ChevronDown class="opacity-50 size-4 shrink-0" />
		</Popover.Trigger>
		<Popover.Content class="p-0 w-[300px]" align="start">
			<Command.Root>
				<Command.Input
					placeholder={`Search ${categoryName || "flavor"} notes...`}
					bind:value={searchQuery}
					class="h-10"
				/>
				<Command.List class="max-h-[300px] overflow-y-auto no-scrollbar">
					{#if searchQuery.trim().length > 0
						&& !contextualFlavors.some(
							(f) => f.toLowerCase() === searchQuery.trim().toLowerCase(),
						)
						&& !allSelectedNotesList.some(
							(n) => n.toLowerCase() === searchQuery.trim().toLowerCase(),
						)}
						<Command.Group heading="Create new" forceMount>
							<Command.Item
								value="__add_new__"
								forceMount
								onSelect={() => handleAdd(searchQuery.trim())}
								class="flex items-center gap-2 text-primary"
							>
								<Plus class="size-4" />
								<span>Add "{searchQuery.trim()}"</span>
							</Command.Item>
						</Command.Group>
					{/if}
					<Command.Empty>
						<div class="p-4 text-center text-muted-foreground text-sm">
							No matching flavors in this category
						</div>
					</Command.Empty>
					<Command.Group
						heading={`${categoryName || ""} Flavors`}
					>
						{#each contextualFlavors as flavor}
							<Command.Item
								value={flavor}
								onSelect={() => handleAdd(flavor)}
								class="flex justify-between items-center"
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
