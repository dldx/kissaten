<script lang="ts">
	import { cn } from "$lib/utils";
	import * as Popover from "$lib/components/ui/popover";

	interface Step {
		name: string;
		level: number; // 0 = top, 1 = category, 2 = subcategory
	}

	interface Props {
		steps: Step[];
		current: number; // 0-based
		currentIcon?: string;
		className?: string;
		onStepClick?: (index: number) => void;
	}

	let {
		steps,
		current,
		currentIcon,
		className = "",
		onStepClick,
	}: Props = $props();

	// Which dot is the trigger open for
	let openIndex = $state<number | null>(null);

	const indentClass: Record<number, string> = {
		0: "pl-0",
		1: "pl-3",
		2: "pl-6",
	};
</script>

<div
	class={cn(
		"flex flex-col items-center gap-3 sm:gap-6 mx-auto w-full max-w-md",
		className,
	)}
>
	{#if currentIcon}
		<div
			class="bg-background bg-white/10 dark:bg-black/20 shadow-2xl backdrop-blur-sm -mb-2 p-2.5 sm:p-4 border-2 border-primary/20 rounded-full text-2xl sm:text-4xl text-center"
		>
			{currentIcon}
		</div>
	{/if}

	<div class="flex justify-center items-center px-4 w-full">
		{#each steps as step, i}
			{@const isCurrent = i === current}
			{@const isCompleted = i < current}
			{@const isHovered = openIndex === i}

			<Popover.Root
				open={isHovered}
				onOpenChange={(o) => {
					if (!o && openIndex === i) openIndex = null;
				}}
			>
				<Popover.Trigger
					type="button"
					onclick={() => onStepClick?.(i)}
					onmouseenter={() => (openIndex = i)}
					onmouseleave={() => (openIndex = null)}
					class="group relative px-1 sm:px-1.5 py-2 focus-visible:outline-none cursor-pointer"
					aria-label="Go to step: {step.name}"
				>
					<div
						class={cn(
							"rounded-full h-2.5 transition-all duration-300",
							isCurrent
								? isHovered
									? "w-12 sm:w-14 bg-primary shadow-md"
									: "w-8 sm:w-10 bg-primary shadow-sm"
								: isCompleted
									? isHovered
										? "w-8 sm:w-10 bg-primary/80"
										: "w-2 sm:w-2.5 bg-primary/60"
									: isHovered
										? "w-8 sm:w-10 bg-muted-foreground/50"
										: "w-2 sm:w-2.5 bg-muted-foreground/30",
						)}
					></div>
				</Popover.Trigger>

				<Popover.Content
					side="top"
					align="center"
					class="z-50 px-2 py-2 pointer-events-none min-w-44"
					sideOffset={10}
				>
					<ul class="flex flex-col gap-0.5">
						{#each steps as s, j}
							{@const jIsCurrent = j === current}
							{@const jIsCompleted = j < current}
							{@const jIsHovered = j === i}
							<li
								class={cn(
									"flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs transition-colors duration-150",
									indentClass[s.level] ?? "pl-0",
									jIsHovered
										? "bg-primary/10 text-foreground font-bold"
										: jIsCurrent
											? "text-primary font-semibold"
											: jIsCompleted
												? "text-muted-foreground"
												: "text-muted-foreground/40",
								)}
							>
								<span
									class={cn(
										"rounded-full shrink-0 transition-colors duration-150",
										s.level === 0 ? "size-1.5" : "size-1",
										jIsHovered || jIsCurrent
											? "bg-primary"
											: jIsCompleted
												? "bg-primary/50"
												: "bg-muted-foreground/30",
									)}
								></span>
								{s.name}
							</li>
						{/each}
					</ul>
				</Popover.Content>
			</Popover.Root>
		{/each}
	</div>
</div>
