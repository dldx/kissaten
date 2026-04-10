<script lang="ts">
	import { cn } from "$lib/utils";

	interface Props {
		steps: number;
		current: number; // 0-based
		currentIcon?: string;
		className?: string;
	}

	let { steps, current, currentIcon, className = "" }: Props = $props();
</script>

<div class={cn("flex flex-col items-center gap-6 mx-auto w-full max-w-md", className)}>
	{#if currentIcon}
		<div class="bg-background bg-white/10 dark:bg-black/20 shadow-2xl backdrop-blur-sm -mb-2 p-4 border-2 border-primary/20 rounded-full text-4xl animate-bounce">
			{currentIcon}
		</div>
	{/if}

	<div class="flex justify-center items-center gap-3 w-full">
		{#each Array.from({ length: steps }) as _, i}
			{@const isCurrent = i === current}
			{@const isCompleted = i < current}

			<div
				class={cn(
					"rounded-full h-2.5 transition-all duration-500",
					isCurrent
						? "w-10 bg-primary shadow-sm"
						: isCompleted
							? "w-2.5 bg-primary/60"
							: "w-2.5 bg-muted-foreground/30"
				)}
			></div>
		{/each}
	</div>
</div>
