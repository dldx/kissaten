<script lang="ts">
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle,
	} from "$lib/components/ui/card";
	import CoffeeBeanImage from "./CoffeeBeanImage.svelte";
	import type { CoffeeBean } from "$lib/api";
	import { api } from "$lib/api";
	import { formatPrice } from "$lib/utils";
	import {
		Droplets,
		Leaf,
		Flame,
		Coffee,
		Star,
		Ban,
		Combine,
	} from "lucide-svelte";

	interface Props {
		bean: CoffeeBean;
		class?: string;
	}

	let { bean, class: className = "" }: Props = $props();

	// Helper to get display data from origins
	const primaryOrigin = $derived(api.getPrimaryOrigin(bean));
	const originDisplay = $derived(api.getOriginDisplayString(bean));
	const processes = $derived(api.getBeanProcesses(bean));
	const varieties = $derived(api.getVarieties(bean));
</script>

<Card class={`hover:shadow-lg dark:hover:shadow-cyan-500/20 dark:hover:shadow-2xl transition-all duration-300 cursor-pointer dark:border-cyan-500/30 dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:hover:border-cyan-400/60 dark:hover:-translate-y-1 ${className}`}>
	<CardHeader class="p-0">
		<!-- Image Section - Emphasized -->
		<CoffeeBeanImage
			{bean}
			class="dark:opacity-90 rounded-t-lg w-full h-full aspect-[4/3]"
		/>

		<div class="p-4 pb-2">
			<CardTitle
				class="bean-title-shadow mb-1 font-semibold text-gray-900 dark:text-cyan-100 text-base line-clamp-2"
			>
				{bean.name}
			</CardTitle>

			<CardDescription class="bean-description-shadow text-gray-600 dark:text-cyan-300/80 text-xs">
				{bean.roaster}
			</CardDescription>
		</div>
	</CardHeader>

	<CardContent class="p-4 pt-0">
		<!-- Origin Info -->
		<div class="mb-2">
			<div class="font-medium text-gray-700 dark:text-emerald-300 text-xs bean-origin-shadow">
				{originDisplay}
			</div>
			{#if primaryOrigin?.elevation && primaryOrigin.elevation > 0}
				<div class="text-gray-500 dark:text-cyan-400/70 text-xs">
					{primaryOrigin.elevation}m elevation
				</div>
			{/if}
		</div>

		<!-- Process & Variety -->
		<div class="flex flex-wrap gap-1 mb-2">
			{#if processes.length > 0}
			<span
				class="inline-flex items-center bg-blue-100 dark:bg-cyan-900/40 px-1.5 py-0.5 dark:border dark:border-cyan-400/50 rounded font-medium text-blue-800 dark:text-cyan-200 text-xs bean-tag-process"
			>
				<Droplets class="mr-1 w-3 h-3" />
				{#each [...new Set(processes)] as process, index (process)}
					{#if index > 0}/{/if}{process}
				{/each}
			</span>
			{/if}
			{#if varieties.length > 0}
			<span
				class="inline-flex items-center bg-green-100 dark:bg-emerald-900/40 px-1.5 py-0.5 dark:border dark:border-emerald-400/50 rounded font-medium text-green-800 dark:text-emerald-200 text-xs bean-tag-variety"
			>
				<Leaf class="mr-1 w-3 h-3" />
				{#each [...new Set(varieties)] as variety, index (variety)}
					{#if index > 0}/{/if}{variety}
				{/each}
			</span>
			{/if}
			{#if bean.roast_level}
				<span
					class="inline-flex items-center bg-orange-100 dark:bg-orange-900/40 px-1.5 py-0.5 dark:border dark:border-orange-400/50 rounded font-medium text-orange-800 dark:text-orange-200 text-xs bean-tag-roast-level"
				>
					<Flame class="mr-1 w-3 h-3" />
					{bean.roast_level}
				</span>
			{/if}
			{#if bean.roast_profile}
				<span
					class="inline-flex items-center bg-purple-100 dark:bg-purple-900/40 px-1.5 py-0.5 dark:border dark:border-purple-400/50 rounded font-medium text-purple-800 dark:text-purple-200 text-xs bean-tag-roast-profile"
				>
					<Coffee class="mr-1 w-3 h-3" />
					{bean.roast_profile}
				</span>
			{/if}
			{#if bean.cupping_score && bean.cupping_score > 0}
				<span
					class="inline-flex items-center bg-yellow-100 dark:bg-yellow-900/40 px-1.5 py-0.5 dark:border dark:border-yellow-400/50 rounded font-medium text-yellow-800 dark:text-yellow-200 text-xs bean-tag-cupping-score"
				>
					<Star class="mr-1 w-3 h-3" />
					{bean.cupping_score}
				</span>
			{/if}
			{#if bean.is_decaf}
				<span
					class="inline-flex items-center bg-red-100 dark:bg-red-900/40 px-1.5 py-0.5 dark:border dark:border-red-400/50 rounded font-medium text-red-800 dark:text-red-200 text-xs bean-tag-decaf"
				>
					<Ban class="mr-1 w-3 h-3" />
					Decaf
				</span>
			{/if}
			{#if !bean.is_single_origin}
				<span
					class="inline-flex items-center bg-indigo-100 dark:bg-pink-900/40 px-1.5 py-0.5 dark:border dark:border-pink-400/50 rounded font-medium text-indigo-800 dark:text-pink-200 text-xs bean-tag-blend"
				>
					<Combine class="mr-1 w-3 h-3" />
					Blend
				</span>
			{/if}
		</div>

		<!-- Tasting Notes -->
		{#if bean.tasting_notes && bean.tasting_notes.length > 0}
			<div class="mb-2">
				<div class="bean-tasting-notes-shadow mb-1 font-medium text-gray-700 dark:text-emerald-300 text-xs">
					Tasting Notes
				</div>
				<div class="flex flex-wrap gap-1">
					{#each bean.tasting_notes as note}
						<span
							class="inline-block bg-gray-100 dark:bg-slate-800/60 bean-tasting-note-shadow px-1.5 py-0.5 dark:border dark:border-cyan-500/30 rounded text-gray-700 dark:text-cyan-200/90 text-xs"
						>
							{note}
						</span>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Price & Weight -->
		<div class="flex justify-between items-center">
			<div class="bean-price-shadow font-bold text-gray-900 dark:text-emerald-300 text-base">
				{#if bean.price}
					{formatPrice(bean.price, bean.currency)}
				{:else}
					<span class="text-gray-400 dark:text-cyan-500/60 text-sm"
						>Price not available</span
					>
				{/if}
			</div>
			<div class="bean-weight-shadow text-gray-500 dark:text-cyan-400/80 text-xs">
				{#if bean.weight}
					{bean.weight}g
				{/if}
			</div>
		</div>

		<!-- Stock Status -->
		{#if bean.in_stock !== null}
			<div class="mt-1">
				<span
					class="inline-block px-1.5 py-0.5 border dark:border rounded font-medium text-xs"
					class:bg-green-100={bean.in_stock}
					class:text-green-800={bean.in_stock}
					class:bg-red-100={!bean.in_stock}
					class:text-red-800={!bean.in_stock}
					class:dark:bg-emerald-900={bean.in_stock}
					class:dark:border-emerald-400={bean.in_stock}
					class:dark:text-emerald-200={bean.in_stock}
					class:dark:bg-red-900={!bean.in_stock}
					class:dark:border-red-400={!bean.in_stock}
					class:dark:text-red-200={!bean.in_stock}
					class:bean-stock-in={bean.in_stock}
					class:bean-stock-out={!bean.in_stock}
				>
					{bean.in_stock ? "In Stock" : "Out of Stock"}
				</span>
			</div>
		{/if}
	</CardContent>
</Card>

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
