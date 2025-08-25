<script lang="ts">
	import { Button as ButtonPrimitive } from "bits-ui";
	import { buttonVariants } from "./index.js";
	import { cn } from "$lib/utils.js";
	import type { Snippet } from "svelte";

	interface Props {
		class?: string;
		variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
		size?: "default" | "sm" | "lg" | "icon";
		builders?: any[];
		children?: Snippet;
		[key: string]: any;
	}

	let {
		class: className = "",
		variant = "default",
		size = "default",
		builders = [],
		children,
		...restProps
	}: Props = $props();
</script>

<ButtonPrimitive.Root
	{builders}
	class={cn(buttonVariants({ variant, size }), className)}
	type="button"
	{...restProps}
>
	{@render children?.()}
</ButtonPrimitive.Root>
