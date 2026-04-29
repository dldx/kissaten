<script lang="ts">
	import type { CoffeeBean } from "$lib/api";
	import { api } from "$lib/api";
	import { page } from "$app/state";
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
	import {
		TASTING_CONVERSATION,
		DEFECT_CONVERSATION,
	} from "$lib/tasting/conversation";

	interface Props {
		bean: CoffeeBean | null | undefined;
		label?: string | null;
		class?: string;
		size?: "sm" | "md" | "lg";
		/** If true, hides tasting notes and farm/region details for a more compact view */
		slim?: boolean;
		/** If true, the tile will not act as a link to the bean page */
		noLink?: boolean;
	}

	let {
		bean,
		label,
		class: className = "",
		size = "md",
		slim = false,
		noLink = false
	}: Props = $props();

	// Derived values for consistent styling
	const isCustomBean = $derived(bean?.bean_url_path?.startsWith('/custom/') || (bean as any)?.is_custom);
	const beanUrl = $derived(bean && !noLink && !isCustomBean ? `/roasters${api.getBeanUrlPath(bean)}` : null);

	const countryNameFromCode = $derived((code: string) => {
		const options = page.data.originOptions || [];
		const country = options.find((o: any) => o.value === code.toUpperCase());
		return country ? country.text : code;
	});

	const originDisplay = $derived(
		bean
			? slim
				? bean.origins?.[0]?.country_full_name || bean.origins?.[0]?.country || ""
				: api.getOriginDisplayString(bean)
			: ""
	);
	const processes = $derived(bean ? api.getBeanProcesses(bean) : []);
	const varieties = $derived(bean ? api.getVarieties(bean) : []);

	function getCategoryForNote(noteName: string) {
		const categories = [...TASTING_CONVERSATION, ...DEFECT_CONVERSATION];
		return categories.find(
			(c) =>
				c.name === noteName ||
				c.flavors?.some((f) => (typeof f === "string" ? f : f.name) === noteName) ||
				c.subTypes?.some(
					(s) => s.name === noteName || s.flavors.some((f) => (typeof f === "string" ? f : f.name) === noteName)
				),
		);
	}
</script>

<svelte:element
	this={beanUrl ? "a" : "div"}
	href={beanUrl}
	class={cn(
		"group relative flex items-center bg-emerald-50/20 hover:bg-emerald-50/30 shadow-sm p-3 border border-emerald-500/20 rounded-lg overflow-hidden transition-all duration-200",
		"dark:hover:shadow-cyan-500/20 dark:hover:shadow-2xl dark:border-cyan-500/30 dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:hover:border-cyan-400/60",
		beanUrl ? "cursor-pointer" : "",
		className,
	)}
>
	{#if bean?.image_data || bean?.image_url}
		<div class="relative mr-3 shrink-0">
			<img
				src={bean.image_data || bean.image_url}
				alt={bean.name}
				class="bg-muted dark:opacity-90 shadow-sm border border-emerald-500/10 dark:border-cyan-500/30 rounded-lg w-16 sm:w-20 h-16 sm:h-20 object-cover"
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
			class="flex justify-center items-center bg-emerald-500/5 dark:bg-cyan-900/20 mr-3 border border-emerald-500/10 dark:border-cyan-500/30 rounded-lg w-16 sm:w-20 h-16 sm:h-20 shrink-0"
		>
			<Sparkles size={20} class="text-emerald-500/40 dark:text-cyan-400/40" />
		</div>
	{/if}

	<div class="flex flex-col flex-1 justify-center min-w-0 text-left">
		<div class="flex flex-col mb-1 sm:mb-1.5 min-w-0">
			<span
				class="mb-0.5 font-bold text-[9px] text-emerald-600 sm:text-[10px] dark:text-cyan-300/80 truncate uppercase tracking-wider"
			>
				{bean?.roaster || "Unknown Roaster"}
			</span>
			<h3
				class="font-extrabold text-foreground dark:text-cyan-100 text-sm sm:text-base truncate leading-tight"
			>
				{bean?.name || label || "Selected Bean"}
			</h3>
		</div>

		{#if bean}
			<!-- Origin Info -->
			{#if !slim}
				<div class="mb-1.5 sm:mb-2 text-wrap">
					<div
						class="font-medium text-[11px] text-gray-700 dark:text-emerald-300 sm:text-xs bean-origin-shadow"
					>
						{originDisplay || (bean.origins?.[0]?.country ? countryNameFromCode(bean.origins?.[0]?.country) : "")}
					</div>
					{#if bean.origins?.[0]?.elevation_min && bean.origins[0].elevation_min > 0}
						<div
							class="text-[10px] text-gray-500 dark:text-cyan-400/70 sm:text-xs"
						>
							{#if bean.origins[0].elevation_max && bean.origins[0].elevation_max > bean.origins[0].elevation_min}
								{bean.origins[0].elevation_min}-{bean.origins[0].elevation_max}m
								elevation
							{:else}
								{bean.origins[0].elevation_min}m elevation
							{/if}
						</div>
					{/if}
				</div>
			{/if}

			<!-- Tags (Process, Variety, etc.) -->
			<div class="flex flex-wrap gap-1 mb-1 sm:mb-1.5 min-w-0 overflow-hidden">
				{#if bean.origins && bean.origins.length > 0}
					<a
						href="/search?origin={encodeURIComponent(bean.origins[0].country)}"
						class="inline-flex items-center bg-red-100 hover:bg-red-200 dark:bg-red-900/40 dark:hover:bg-red-900/60 px-1.5 py-0.5 dark:border dark:border-red-400/50 rounded max-w-[120px] text-[10px] text-red-800 dark:text-red-200 sm:text-xs transition-colors shrink-0"
					>
						<iconify-icon
							icon="circle-flags:{bean.origins[0].country?.toLowerCase()}"
							class="mr-1 w-2.5 h-2.5 shrink-0"
						></iconify-icon>
						<span class="truncate">{bean.origins[0].country_full_name || countryNameFromCode(bean.origins[0].country)}</span>
					</a>
				{/if}
				{#if varieties.length > 0}
				<span
					class="inline-flex items-center bg-green-100 dark:bg-emerald-900/40 px-1 sm:px-1.5 py-0.5 dark:border dark:border-emerald-400/50 rounded font-medium text-[10px] text-green-800 dark:text-emerald-200 sm:text-xs bean-tag-variety"
				>
					<Leaf class="mr-0.5 sm:mr-1 w-2.5 sm:w-3 h-2.5 sm:h-3" />
					<span class="line-clamp-1">
						{#each [...new Set(varieties)] as variety, index (variety)}
							{#if index > 0}/&#8203;{/if}{variety}
						{/each}
					</span>
				</span>
				{/if}
				{#if processes.length > 0}
				<span
					class="inline-flex items-center bg-blue-100 dark:bg-cyan-900/40 px-1 sm:px-1.5 py-0.5 dark:border dark:border-cyan-400/50 rounded font-medium text-[10px] text-blue-800 dark:text-cyan-200 sm:text-xs bean-tag-process"
				>
					<Droplets
						class="mr-0.5 sm:mr-1 w-2.5 sm:w-3 h-2.5 sm:h-3"
					/>
					<span class="line-clamp-1">
						{#each [...new Set(processes)] as process, index (process)}
							{#if index > 0}/{/if}{process}
						{/each}
					</span>
				</span>
				{/if}
				{#if bean.roast_level}
					<a
						href="/search?roast_level={encodeURIComponent(bean.roast_level)}"
						class="inline-flex items-center bg-orange-100 hover:bg-orange-200 dark:bg-orange-900/40 dark:hover:bg-orange-900/60 px-1 py-0.5 dark:border dark:border-orange-400/50 rounded font-medium text-[10px] text-orange-800 dark:text-orange-200 sm:text-xs transition-colors shrink-0"
					>
						<Flame class="mr-0.5 sm:mr-1 w-2.5 sm:w-3 h-2.5 sm:h-3 shrink-0" />
						{bean.roast_level}
					</a>
				{/if}
				{#if bean.roast_profile}
					<a
						href="/search?roast_profile={encodeURIComponent(bean.roast_profile)}"
						class="inline-flex items-center bg-purple-100 hover:bg-purple-200 dark:bg-purple-900/40 dark:hover:bg-purple-900/60 px-1 py-0.5 dark:border dark:border-purple-400/50 rounded font-medium text-[10px] text-purple-800 dark:text-purple-200 sm:text-xs transition-colors shrink-0"
					>
						<Coffee class="mr-0.5 sm:mr-1 w-2.5 sm:w-3 h-2.5 sm:h-3 shrink-0" />
						{bean.roast_profile}
					</a>
				{/if}
				{#if bean.is_decaf}
					<a
						href="/search?is_decaf=true"
						class="inline-flex items-center bg-red-100 hover:bg-red-200 dark:bg-red-900/40 dark:hover:bg-red-900/60 px-1 py-0.5 dark:border dark:border-red-400/50 rounded font-medium text-[10px] text-red-800 dark:text-red-200 sm:text-xs transition-colors shrink-0"
					>
						<Ban class="mr-0.5 sm:mr-1 w-2.5 sm:w-3 h-2.5 sm:h-3 shrink-0" />
						Decaf
					</a>
				{/if}
				{#if !bean.is_single_origin}
					<a
						href="/search?is_single_origin=false"
						class="inline-flex items-center bg-indigo-100 hover:bg-indigo-200 dark:bg-pink-900/40 dark:hover:bg-pink-900/60 px-1 py-0.5 dark:border dark:border-pink-400/50 rounded font-medium text-[10px] text-indigo-800 dark:text-pink-200 sm:text-xs transition-colors shrink-0"
					>
						<Combine class="mr-0.5 sm:mr-1 w-2.5 sm:w-3 h-2.5 sm:h-3 shrink-0" />
						Blend
					</a>
				{/if}
			</div>

			<!-- Tasting Notes -->
			{#if !slim && bean.tasting_notes && bean.tasting_notes.length > 0}
				<div class="flex flex-wrap gap-1 max-h-12 overflow-hidden">
					{#each bean.tasting_notes as note}
						{@const noteName = typeof note === "string" ? note : note.note}
						{@const primaryCategory = typeof note === "string" ? null : note.primary_category}
						{@const cat = primaryCategory ? null : getCategoryForNote(noteName)}
						{@const categoryName = primaryCategory || (cat?.isDefect ? "defects" : cat?.name) || ""}
						{@const flavourCategoryColors = getFlavourCategoryColors(categoryName)}
						<a
							href="/search?tasting_notes_query={encodeURIComponent(noteName)}"
							class="inline-block {flavourCategoryColors.bg} {flavourCategoryColors.darkBg} {flavourCategoryColors.text} {flavourCategoryColors.darkText} hover:opacity-80 transition-opacity px-1 py-0.5 dark:border dark:border-cyan-500/30 rounded text-[10px] sm:text-xs whitespace-nowrap"
						>
							{noteName}
						</a>
					{/each}
				</div>
			{/if}
		{/if}
	</div>
</svelte:element>
