<script lang="ts">
	import type { CoffeeBean } from "$lib/api";
	import { api } from "$lib/api";
	import {
		Droplets,
		Leaf,
		Flame,
		Coffee,
		Star,
		Ban,
		Combine,
		Sparkles,
	} from "lucide-svelte";
	import { cn, getFlavourCategoryColors } from "$lib/utils";

	interface Props {
		bean: CoffeeBean | null | undefined;
		label?: string | null;
		class?: string;
		size?: "sm" | "md" | "lg";
	}

	let { bean, label, class: className = "", size = "md" }: Props = $props();

	// Derived values for consistent styling
	const beanUrl = $derived(bean ? `/roasters${api.getBeanUrlPath(bean)}` : null);
	const originDisplay = $derived(bean ? api.getOriginDisplayString(bean) : "");
	const processes = $derived(bean ? api.getBeanProcesses(bean) : []);
	const varieties = $derived(bean ? api.getVarieties(bean) : []);
</script>

<svelte:element
	this={beanUrl ? "a" : "div"}
	href={beanUrl}
	class={cn(
		"group relative flex items-start bg-emerald-50/20 hover:bg-emerald-50/30 shadow-sm p-4 border border-emerald-500/20 rounded-lg overflow-hidden transition-all duration-200",
		"dark:hover:shadow-cyan-500/20 dark:hover:shadow-2xl dark:border-cyan-500/30 dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:hover:border-cyan-400/60",
		beanUrl ? "cursor-pointer" : "",
		className,
	)}
>
	{#if bean?.image_url}
		<div class="relative shrink-0">
			<img
				src={bean.image_url}
				alt={bean.name}
				class="bg-muted dark:opacity-90 shadow-sm border border-emerald-500/10 dark:border-cyan-500/30 rounded-lg w-20 h-20 object-cover"
			/>
			{#if bean.cupping_score}
				<div
					class="-top-1.5 -right-1.5 absolute bg-yellow-400 dark:bg-yellow-500 shadow-sm px-1.5 py-0.5 rounded-full font-bold text-[10px] text-yellow-900"
				>
					{bean.cupping_score}
				</div>
			{/if}
		</div>
	{:else}
		<div
			class="flex justify-center items-center bg-emerald-500/5 dark:bg-cyan-900/20 border border-emerald-500/10 dark:border-cyan-500/30 rounded-lg w-20 h-20 shrink-0"
		>
			<Sparkles size={24} class="text-emerald-500/40 dark:text-cyan-400/40" />
		</div>
	{/if}

	<div class="flex flex-col flex-1 justify-center ml-4 pr-2 min-w-0 text-left">
		<div class="flex flex-col mb-1.5">
			<span
				class="mb-0.5 font-bold text-[10px] text-emerald-600 dark:text-cyan-300/80 uppercase tracking-wider"
			>
				{bean?.roaster || "Unknown Roaster"}
			</span>
			<h3
				class="font-extrabold text-foreground dark:text-cyan-100 text-base truncate leading-tight"
			>
				{bean?.name || label || "Selected Bean"}
			</h3>
		</div>

		{#if bean}
			<!-- Origin Info -->
			<div
				class="mb-1.5 font-medium text-[11px] text-gray-700 dark:text-emerald-300 leading-tight"
			>
				{originDisplay}
			</div>

			<!-- Tags (Process, Variety, etc.) -->
			<div class="flex flex-wrap gap-1 mb-1.5">
				{#if processes.length > 0}
					<span
						class="inline-flex items-center bg-blue-100 dark:bg-cyan-900/40 px-1 py-0.5 dark:border dark:border-cyan-400/50 rounded font-medium text-[9px] text-blue-800 dark:text-cyan-200"
					>
						<Droplets class="mr-0.5 w-2.5 h-2.5" />
						<span class="line-clamp-1">
							{#each [...new Set(processes)] as process, index (process)}
								{#if index > 0}/{/if}{process}
							{/each}
						</span>
					</span>
				{/if}
				{#if varieties.length > 0}
					<span
						class="inline-flex items-center bg-green-100 dark:bg-emerald-900/40 px-1 py-0.5 dark:border dark:border-emerald-400/50 rounded font-medium text-[9px] text-green-800 dark:text-emerald-200"
					>
						<Leaf class="mr-0.5 w-2.5 h-2.5" />
						<span class="line-clamp-1">
							{#each [...new Set(varieties)] as variety, index (variety)}
								{#if index > 0}/&#8203;{/if}{variety}
							{/each}
						</span>
					</span>
				{/if}
				{#if bean.roast_level}
					<span
						class="inline-flex items-center bg-orange-100 dark:bg-orange-900/40 px-1 py-0.5 dark:border dark:border-orange-400/50 rounded font-medium text-[9px] text-orange-800 dark:text-orange-200"
					>
						<Flame class="mr-0.5 w-2.5 h-2.5" />
						{bean.roast_level}
					</span>
				{/if}
				{#if bean.roast_profile}
					<span
						class="inline-flex items-center bg-purple-100 dark:bg-purple-900/40 px-1 py-0.5 dark:border dark:border-purple-400/50 rounded font-medium text-[9px] text-purple-800 dark:text-purple-200"
					>
						<Coffee class="mr-0.5 w-2.5 h-2.5" />
						{bean.roast_profile}
					</span>
				{/if}
				{#if bean.is_decaf}
					<span
						class="inline-flex items-center bg-red-100 dark:bg-red-900/40 px-1 py-0.5 dark:border dark:border-red-400/50 rounded font-medium text-[9px] text-red-800 dark:text-red-200"
					>
						<Ban class="mr-0.5 w-2.5 h-2.5" />
						Decaf
					</span>
				{/if}
				{#if !bean.is_single_origin}
					<span
						class="inline-flex items-center bg-indigo-100 dark:bg-pink-900/40 px-1 py-0.5 dark:border dark:border-pink-400/50 rounded font-medium text-[9px] text-indigo-800 dark:text-pink-200"
					>
						<Combine class="mr-0.5 w-2.5 h-2.5" />
						Blend
					</span>
				{/if}
			</div>

			<!-- Tasting Notes -->
			{#if bean.tasting_notes && bean.tasting_notes.length > 0}
				<div class="flex flex-wrap gap-1">
					{#each bean.tasting_notes as note}
						{@const flavourCategoryColors = getFlavourCategoryColors(
							typeof note === "string" ? "" : (note.primary_category ?? ""),
						)}
						<span
							class="inline-block {flavourCategoryColors.bg} {flavourCategoryColors.darkBg} {flavourCategoryColors.text} {flavourCategoryColors.darkText} px-1 py-0.5 dark:border dark:border-cyan-500/30 rounded text-[9px]"
						>
							{typeof note === "string" ? note : note.note}
						</span>
					{/each}
				</div>
			{/if}
		{/if}
	</div>
</svelte:element>
