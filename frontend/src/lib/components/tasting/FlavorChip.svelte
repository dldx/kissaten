<script lang="ts">
	import { getFlavourCategoryColors, cn } from "$lib/utils";
	import { Check } from "lucide-svelte";

	interface Props {
		name: string;
		categoryName: string;
		selected?: boolean;
		count?: number;
		onSelect?: () => void;
		className?: string;
	}

	let { name, categoryName, selected = false, count, onSelect, className = "" }: Props = $props();

	const colors = $derived(getFlavourCategoryColors(categoryName));
</script>

<button
	type="button"
	onclick={onSelect}
	class={cn(
		"flex items-center gap-2 px-4 py-2.5 border rounded-full font-medium text-sm transition-all duration-300 group relative overflow-hidden",
		selected
			? `${colors.bg} ${colors.text} ${colors.border} shadow-md ring-1 ring-inset ${colors.border} scale-105`
			: "bg-background border-muted hover:border-muted-foreground/30 hover:bg-muted/30 text-muted-foreground",
		className
	)}
>
	<span class="relative z-10">{name}</span>
	
	{#if count !== undefined && count > 0}
		<span class={cn(
			"ml-1 px-1.5 py-0.5 rounded-full text-[10px] font-bold transition-colors duration-300",
			selected ? "bg-black/20 text-white" : "bg-muted text-muted-foreground"
		)}>
			{count}
		</span>
	{/if}

	{#if selected}
		<Check size={14} strokeWidth={2.5} class="relative z-10 animate-in duration-300 zoom-in" />
	{/if}
</button>
