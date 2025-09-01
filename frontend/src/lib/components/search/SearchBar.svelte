<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Search } from "lucide-svelte";
	import { goto } from "$app/navigation";

	interface Props {
		value: string;
		placeholder?: string;
		class?: string;
		showButton?: boolean;
		buttonText?: string;
		onSearch?: (query: string) => void;
	}

	let {
		value = $bindable(),
		placeholder = "Search for beans, roasters, origins, tasting notes...",
		class: className = "",
		showButton = true,
		buttonText = "Search",
		onSearch
	}: Props = $props();

	function handleSearch() {
		if (value.trim()) {
			if (onSearch) {
				onSearch(value.trim());
			} else {
				// Default behavior: navigate to search page
				goto(`/search?q=${encodeURIComponent(value.trim())}`);
			}
		}
	}

	function handleKeyPress(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			handleSearch();
		}
	}
</script>

<div class={`flex gap-2 ${className}`}>
	<div class="relative flex-1">
		<Search class="top-1/2 left-3 absolute w-4 h-4 text-muted-foreground -translate-y-1/2 transform" />
		<Input
			bind:value
			{placeholder}
			class="pl-10"
			onkeypress={handleKeyPress}
		/>
	</div>
	{#if showButton}
		<Button onclick={handleSearch} size="default">{buttonText}</Button>
	{/if}
</div>
