<script lang="ts">
	import { getFlavourCategoryColors, cn } from "$lib/utils";
	import { Check } from "lucide-svelte";
	import { fade } from "svelte/transition";

	interface Props {
		name: string;
		emoji: string;
		selected?: boolean;
		onSelect?: () => void;
		className?: string;
	}

	let { name, emoji, selected = false, onSelect, className = "" }: Props = $props();

	const colors = $derived(getFlavourCategoryColors(name));
</script>

<button
	type="button"
	onclick={onSelect}
	class={cn(
		"group relative flex flex-col justify-center items-center gap-3 p-6 border-2 rounded-2xl text-center active:scale-95 transition-all duration-300",
		selected
			? `${colors.bg} ${colors.border} ${colors.text} shadow-lg ring-2 ring-offset-2 ring-primary/20 ${colors.darkBg} ${colors.darkBorder} ${colors.darkText}`
			: "bg-background border-muted hover:border-muted-foreground/30 hover:bg-muted/30 dark:bg-card dark:hover:bg-muted/10",
		className
	)}
>
	<span class="text-4xl group-hover:scale-110 transition-transform duration-300">{emoji}</span>
	<span class="font-bold text-sm uppercase tracking-wider">{name}</span>

	{#if selected}
		<div
			transition:fade={{ duration: 200 }}
			class="-top-2 -right-2 absolute bg-primary shadow-md p-1 border-2 border-background rounded-full text-primary-foreground"
		>
			<Check size={14} strokeWidth={3} />
		</div>
	{/if}
</button>
