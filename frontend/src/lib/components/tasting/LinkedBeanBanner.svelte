<script lang="ts">
	import { Coffee, X } from "lucide-svelte";
	import { Button } from "$lib/components/ui/button/index.js";
	import { slide } from "svelte/transition";
	import type { CoffeeBean } from "$lib/api";

	interface Props {
		beanLabel: string;
		beanUrlPath: string;
		beanData: CoffeeBean;
		onUnlink: () => void;
	}

	let { beanLabel, beanUrlPath, beanData, onUnlink }: Props = $props();
</script>

<div
	class="flex flex-wrap justify-between items-center gap-2 bg-primary/5 mb-6 p-3 border border-primary/20 rounded-xl w-full"
	transition:slide
>
	<a
		href={`/roasters${beanUrlPath}`}
		class="group flex items-center gap-3 hover:opacity-80 transition-opacity"
	>
		<div class="bg-primary/10 group-hover:bg-primary/20 p-2 rounded-lg text-primary transition-colors">
			<Coffee size={20} />
		</div>
		<div class="flex flex-col">
			<span class="font-bold text-sm group-hover:underline underline-offset-4 text-wrap leading-tight">{beanLabel}</span>
			<span class="text-muted-foreground text-xs">Tasting linked to this bean (click to view)</span>
		</div>
	</a>
	<Button
		variant="ghost"
		size="sm"
		class="h-8 text-muted-foreground hover:text-destructive text-xs"
		onclick={onUnlink}
		aria-label="Unlink bean"
	>
		<X size={14} class="mr-1" />
		Unlink
	</Button>
</div>
