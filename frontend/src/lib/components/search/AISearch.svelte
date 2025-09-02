<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Sparkles, Loader2, Filter } from "lucide-svelte";

	interface Props {
		value: string;
		loading?: boolean;
		available?: boolean;
		placeholder?: string;
		class?: string;
		showFilters?: boolean;
		onSearch: (query: string) => void | Promise<void>;
		onToggleFilters?: () => void;
	}

	const placeholders = [
		"Find me coffee beans that taste like a pina colada...",
		"Light roast from european roasters with berry notes...",
		"Panama Geisha coffees with funky flavours...",
		"Colombian coffee with citrus flavors above 1800m...",
		"Pink bourbons from uk roasters...",
		"Chocolate coffee that's not bitter...",
	];

	let {
		value = $bindable(),
		loading = false,
		available = true,
		placeholder = "Describe the beans you're looking for...", // Random placeholder
		class: className = "",
		showFilters = false,
		onSearch,
		onToggleFilters,
	}: Props = $props();

	async function handleSearch() {
		if (!value || !available) return;
		await onSearch(value);
	}

	function handleKeyPress(event: KeyboardEvent) {
		if (event.key === "Enter") {
			handleSearch();
		}
	}

	// Change the placeholder every 5 seconds
	setInterval(() => {
		placeholder =
			placeholders[Math.floor(Math.random() * placeholders.length)];
	}, 3000);
</script>

{#if available}
	<div class={`space-y-2 ${className} flex flex-row w-full gap-2`}>
		<div class="relative flex-1">
			<Sparkles
				class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform"
			/>
			<Input
				type="search"
				bind:value
				{placeholder}
				class="pl-10"
				onkeypress={handleKeyPress}
				disabled={loading}
			/>
		</div>
		<div class="flex gap-2">
			<Button
				variant="secondary"
				size="default"
				onclick={handleSearch}
				disabled={loading || !value.trim()}
				class="hidden md:inline-flex"
			>
				{#if loading}
					<Loader2 class="mr-2 w-3 h-3 animate-spin" />
					Digging deep into the vault...
				{:else}
					<Sparkles class="mr-2 w-3 h-3" />
					Find some brews!
				{/if}
			</Button>
			{#if onToggleFilters}
				<Button
					variant="ghost"
					size="default"
					onclick={onToggleFilters}
					class="lg:hidden px-3"
				>
					<Filter class="w-4 h-4" />
				</Button>
			{/if}
		</div>
	</div>
	{#if value}
		<p class="mt-1 text-muted-foreground text-xs">
			Tweak the advanced filters if our smart search doesn't give you what
			you're looking for.
		</p>
	{/if}
{/if}
