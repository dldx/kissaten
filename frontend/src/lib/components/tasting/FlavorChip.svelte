<script lang="ts">
	import { getFlavourCategoryColors, cn } from "$lib/utils";
	import { Check } from "lucide-svelte";

	interface Props {
		name: string;
		categoryName: string;
		selected?: boolean;
		onSelect?: () => void;
		className?: string;
	}

	let { name, categoryName, selected = false, onSelect, className = "" }: Props = $props();

	const colors = $derived(getFlavourCategoryColors(categoryName));
</script>

<button
	type="button"
	onclick={onSelect}
	class={cn(
		"flex items-center gap-2 px-4 py-2.5 border rounded-full font-medium text-sm transition-all duration-200",
		selected
			? `${colors.bg} ${colors.text} ${colors.border} ${colors.darkBg} ${colors.darkText} ${colors.darkBorder} shadow-sm ring-1 ring-inset ${colors.border}`
			: "bg-background border-muted hover:border-muted-foreground/30 hover:bg-muted/30 text-muted-foreground dark:bg-card dark:hover:bg-muted/10",
		className
	)}
>
	{name}
	{#if selected}
		<Check size={14} strokeWidth={2.5} class="animate-in duration-300 zoom-in" />
	{/if}
</button>
