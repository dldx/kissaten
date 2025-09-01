<script lang="ts">
	import { cn } from "$lib/utils.js";

	interface Props {
		class?: string;
		value?: string | number;
		placeholder?: string;
		readonly?: boolean;
		[key: string]: any;
	}

	let {
		class: className = "",
		value = $bindable(),
		placeholder = "",
		readonly = false,
		...restProps
	}: Props = $props();

	let inputElement: HTMLInputElement;
</script>

<input
	bind:this={inputElement}
	class={cn(
		"flex bg-background file:bg-transparent disabled:opacity-50 px-3 py-2 border border-input file:border-0 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ring-offset-background focus-visible:ring-offset-2 w-full h-10 file:font-medium placeholder:text-muted-foreground text-sm file:text-sm disabled:cursor-not-allowed",
		className
	)}
	bind:value
	{placeholder}
	{readonly}
	{...restProps}
/>
