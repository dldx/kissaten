<script lang="ts">
    import { Funnel } from "lucide-svelte";
	import { Button, type ButtonProps } from "../ui/button";
	let {
		onToggleFilters,
		hasActiveFilters,
		size = "default",
		variant = "ghost",
        showLabel = false,
	}: {
		onToggleFilters: (() => void) | undefined;
		hasActiveFilters: boolean;
		size?: ButtonProps["size"];
		variant?: ButtonProps["variant"];
        showLabel?: boolean;
	} = $props();
	</script>
				<Button
					variant={variant}
					size={size}
					onclick={onToggleFilters}
					class="relative px-3 {hasActiveFilters
						? 'ring-2 ring-orange-500 dark:ring-emerald-500/50'
						: ''}"
					title="Toggle advanced filters panel"
					aria-label="Toggle advanced filters"
				>
					<Funnel
						class="w-4 h-4 {hasActiveFilters
							? 'text-orange-600 dark:text-emerald-400'
							: ''}"
					/>
                    {#if showLabel}
                        <span class="ml-2">Advanced filters</span>
                    {/if}
					{#if hasActiveFilters}
						<div
							class="top-0 right-0 absolute bg-orange-500 dark:bg-emerald-500 rounded-full w-2 h-2 -translate-y-1 translate-x-1 transform"
						></div>
						{/if}
					</Button>