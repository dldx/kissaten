<script lang="ts">
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "$lib/components/ui/card";
	import CoffeeBeanImage from "./CoffeeBeanImage.svelte";
	import type { CoffeeBean } from "$lib/api";
	import { api } from "$lib/api";
    import { formatPrice } from "$lib/utils";

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

<Card class={`hover:shadow-lg transition-shadow cursor-pointer ${className}`}>
	<CardHeader class="p-0">
		<!-- Image Section - Emphasized -->
		<CoffeeBeanImage {bean} class="rounded-t-lg w-full h-full aspect-[4/3]" />

		<div class="p-4 pb-2">
			<CardTitle class="mb-1 font-semibold text-gray-900 text-base line-clamp-2">
				{bean.name}
			</CardTitle>

			<CardDescription class="text-gray-600 text-xs">
				{bean.roaster}
			</CardDescription>
		</div>
	</CardHeader>

	<CardContent class="p-4 pt-0">
		<!-- Origin Info -->
		<div class="mb-2">
			<div class="font-medium text-gray-700 text-xs">
				{originDisplay}
			</div>
			{#if primaryOrigin?.elevation && primaryOrigin.elevation > 0}
				<div class="text-gray-500 text-xs">{primaryOrigin.elevation}m elevation</div>
			{/if}
		</div>

		<!-- Process & Variety -->
		<div class="flex flex-wrap gap-1 mb-2">
			{#each processes as process}
				<span class="inline-block bg-blue-100 px-1.5 py-0.5 rounded font-medium text-blue-800 text-xs">
					{process}
				</span>
			{/each}
			{#each varieties as variety}
				<span class="inline-block bg-green-100 px-1.5 py-0.5 rounded font-medium text-green-800 text-xs">
					{variety}
				</span>
			{/each}
			{#if bean.roast_level}
				<span class="inline-block bg-orange-100 px-1.5 py-0.5 rounded font-medium text-orange-800 text-xs">
					{bean.roast_level}
				</span>
			{/if}
			{#if bean.roast_profile}
				<span class="inline-block bg-purple-100 px-1.5 py-0.5 rounded font-medium text-purple-800 text-xs">
					{bean.roast_profile}
				</span>
			{/if}
			{#if bean.cupping_score && bean.cupping_score > 0}
				<span class="inline-block bg-yellow-100 px-1.5 py-0.5 rounded font-medium text-yellow-800 text-xs">
					★ {bean.cupping_score}
				</span>
			{/if}
			{#if bean.is_decaf}
				<span class="inline-block bg-red-100 px-1.5 py-0.5 rounded font-medium text-red-800 text-xs">
					Decaf
				</span>
			{/if}
			{#if !bean.is_single_origin}
				<span class="inline-block bg-indigo-100 px-1.5 py-0.5 rounded font-medium text-indigo-800 text-xs">
					Blend
				</span>
			{/if}
		</div>

		<!-- Tasting Notes -->
		{#if bean.tasting_notes && bean.tasting_notes.length > 0}
			<div class="mb-2">
				<div class="mb-1 font-medium text-gray-700 text-xs">Tasting Notes</div>
				<div class="flex flex-wrap gap-1">
					{#each bean.tasting_notes.slice(0, 2) as note}
						<span class="inline-block bg-gray-100 px-1.5 py-0.5 rounded text-gray-700 text-xs">
							{note}
						</span>
					{/each}
					{#if bean.tasting_notes.length > 2}
						<span class="inline-block bg-gray-100 px-1.5 py-0.5 rounded text-gray-500 text-xs">
							+{bean.tasting_notes.length - 2} more
						</span>
					{/if}
				</div>
			</div>
		{/if}

		<!-- Price & Weight -->
		<div class="flex justify-between items-center">
			<div class="font-bold text-gray-900 text-base">
				{#if bean.price}
					{formatPrice(bean.price, bean.currency)}
				{:else}
					<span class="text-gray-400 text-sm">Price not available</span>
				{/if}
			</div>
			<div class="text-gray-500 text-xs">
				{#if bean.weight}
					{bean.weight}g
				{/if}
			</div>
		</div>

		<!-- Stock Status -->
		{#if bean.in_stock !== null}
			<div class="mt-1">
				<span
					class="inline-block px-1.5 py-0.5 rounded font-medium text-xs"
					class:bg-green-100={bean.in_stock}
					class:text-green-800={bean.in_stock}
					class:bg-red-100={!bean.in_stock}
					class:text-red-800={!bean.in_stock}
				>
					{bean.in_stock ? 'In Stock' : 'Out of Stock'}
				</span>
			</div>
		{/if}
	</CardContent>
</Card>

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
