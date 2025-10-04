<script lang="ts">
	import { Switch as SwitchPrimitive } from "bits-ui";
	import { cn, type WithoutChildrenOrChild } from "$lib/utils.js";

	let {
		ref = $bindable(null),
		class: className,
		checked = $bindable(false),
		...restProps
	}: WithoutChildrenOrChild<SwitchPrimitive.RootProps> = $props();
</script>

<SwitchPrimitive.Root
	bind:ref
	bind:checked
	data-slot="switch"
	class={cn(
		"peer inline-flex items-center data-[state=checked]:bg-primary data-[state=unchecked]:bg-input dark:data-[state=unchecked]:bg-[oklch(0.4_0.09_197.27)] disabled:opacity-50 shadow-xs border border-transparent focus-visible:border-ring rounded-full outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 w-8 h-[1.15rem] transition-all disabled:cursor-not-allowed shrink-0",
		className
	)}
	{...restProps}
>
	<SwitchPrimitive.Thumb
		data-slot="switch-thumb"
		class={cn(
			"block bg-background dark:data-[state=checked]:bg-primary-foreground dark:data-[state=unchecked]:bg-foreground rounded-full ring-0 size-4 transition-transform data-[state=checked]:translate-x-[calc(100%-2px)] data-[state=unchecked]:translate-x-0 pointer-events-none"
		)}
	/>
</SwitchPrimitive.Root>
