<script lang="ts">
	import { useDroppable } from "@dnd-kit-svelte/svelte";
	import { Trash2 } from "lucide-svelte";
	import { cn } from "$lib/utils";

	interface Props {
		active: boolean;
	}

	let { active }: Props = $props();

	const droppable = useDroppable({
		id: "trash",
	});
</script>

<div
	{@attach droppable.ref}
	class={cn(
		"fixed bottom-50 left-1/2 -translate-x-1/2 z-100 transition-all duration-300 pointer-events-none group",
		active
			? "translate-y-0 opacity-100 pointer-events-auto"
			: "translate-y-20 opacity-0",
	)}
>
	<div
		class={cn(
			"flex items-center gap-3 px-8 py-4 rounded-full border-2 bg-background shadow-2xl transition-all",
			droppable.isDropTarget.current
				? "border-destructive  scale-110 text-destructive"
				: "border-muted-foreground/20 text-muted-foreground",
		)}
	>
		<Trash2
			class={cn(
				"w-5 h-5",
				droppable.isDropTarget.current && "animate-bounce",
			)}
		/>
		<span class="font-bold uppercase tracking-widest text-sm">
			{droppable.isDropTarget.current
				? "Drop to remove"
				: "Drag here to remove"}
		</span>
	</div>
</div>
