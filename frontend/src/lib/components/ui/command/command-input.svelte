<script lang="ts">
	import { Command as CommandPrimitive } from "bits-ui";
	import SearchIcon from "@lucide/svelte/icons/search";
	import type { Component } from "svelte";
	import type { IconProps } from "@lucide/svelte";
	import { cn } from "$lib/utils.js";

	type Props = CommandPrimitive.InputProps & {
		icon?: Component<IconProps> | null;
		iconClass?: string;
	};

	let {
		ref = $bindable(null),
		class: className,
		value = $bindable(""),
		icon: Icon = SearchIcon,
		iconClass = "",
		...restProps
	}: Props = $props();
</script>

<div class="flex items-center gap-2 pr-8 pl-3 border-b h-9" data-slot="command-input-wrapper">
	{#if Icon}
		<Icon class={cn("opacity-50 size-4 shrink-0", iconClass)} />
	{/if}
	<CommandPrimitive.Input
		data-slot="command-input"
		class={cn(
			"flex bg-transparent disabled:opacity-50 py-3 rounded-md outline-hidden w-full h-10 placeholder:text-muted-foreground text-sm disabled:cursor-not-allowed",
			className
		)}
		bind:ref
		{...restProps}
		bind:value
	/>
</div>
