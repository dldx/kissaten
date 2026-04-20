<script lang="ts">
	import { useSortable } from "@dnd-kit-svelte/svelte/sortable";
	import { cn } from "$lib/utils";
	import { Grip } from "lucide-svelte"; // Simple icon for handle or skip

	interface Props {
		note: string;
		index: number;
		colors: any;
		isDefect?: boolean;
		onRegister?: (
			note: string,
			getInstance: () => { index: number },
		) => void;
	}

	let { note, index, colors, isDefect = false, onRegister }: Props = $props();

	const sortable = useSortable({
		id: () => note,
		index: () => index,
	});

	$effect(() => {
		onRegister?.(note, () => sortable.sortable);
	});
	import { fade } from "svelte/transition";
</script>

<div
	{@attach sortable.ref}
	transition:fade={{ duration: 200 }}
	class={cn(
		"flex items-center gap-2 shadow-sm hover:shadow-md px-3 py-2 border rounded-full font-medium text-sm transition-shadow cursor-grab active:cursor-grabbing select-none",
		isDefect
			? "border-destructive/30 bg-destructive/10"
			: cn(
					colors.bg,
					colors.text,
					colors.border,
					colors.darkBg,
					colors.darkText,
					colors.darkBorder,
				),
		sortable.isDragging.current ? "opacity-30 z-50 pointer-events-none" : "opacity-100",
	)}
>
	<span class="opacity-40 shrink-0">⠿</span>
	{note}
</div>
