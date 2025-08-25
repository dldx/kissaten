<script lang="ts">
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "$lib/components/ui/card";
	import CoffeeBeanImage from "./CoffeeBeanImage.svelte";
	import type { CoffeeBean } from "$lib/api";

	interface Props {
		bean: CoffeeBean;
		class?: string;
	}

	let { bean, class: className = "" }: Props = $props();
</script>

<Card class={`hover:shadow-lg transition-shadow cursor-pointer ${className}`}>
	<CardHeader class="pb-3">
		<!-- Image Section -->
		<CoffeeBeanImage {bean} class="w-full aspect-square" />

		<CardTitle class="font-semibold text-gray-900 text-lg line-clamp-2">
			{bean.name}
		</CardTitle>

		<CardDescription class="text-gray-600 text-sm">
			{bean.roaster}
		</CardDescription>
	</CardHeader>

	<CardContent class="pt-0">
		<!-- Origin Info -->
		<div class="mb-3">
			<div class="font-medium text-gray-700 text-sm">
				{#if bean.country_full_name}
					{bean.country_full_name}
				{:else}
					{bean.country}
				{/if}
				{#if bean.region}
					, {bean.region}
				{/if}
			</div>
			{#if bean.elevation > 0}
				<div class="text-gray-500 text-xs">{bean.elevation}m elevation</div>
			{/if}
		</div>

		<!-- Process & Variety -->
		<div class="flex flex-wrap gap-1 mb-3">
			{#if bean.process}
				<span class="inline-block bg-blue-100 px-2 py-1 rounded font-medium text-blue-800 text-xs">
					{bean.process}
				</span>
			{/if}
			{#if bean.variety}
				<span class="inline-block bg-green-100 px-2 py-1 rounded font-medium text-green-800 text-xs">
					{bean.variety}
				</span>
			{/if}
			{#if bean.roast_level}
				<span class="inline-block bg-orange-100 px-2 py-1 rounded font-medium text-orange-800 text-xs">
					{bean.roast_level}
				</span>
			{/if}
		</div>

		<!-- Tasting Notes -->
		{#if bean.tasting_notes && bean.tasting_notes.length > 0}
			<div class="mb-3">
				<div class="mb-1 font-medium text-gray-700 text-xs">Tasting Notes</div>
				<div class="flex flex-wrap gap-1">
					{#each bean.tasting_notes.slice(0, 3) as note}
						<span class="inline-block bg-gray-100 px-2 py-1 rounded text-gray-700 text-xs">
							{note}
						</span>
					{/each}
					{#if bean.tasting_notes.length > 3}
						<span class="inline-block bg-gray-100 px-2 py-1 rounded text-gray-500 text-xs">
							+{bean.tasting_notes.length - 3} more
						</span>
					{/if}
				</div>
			</div>
		{/if}

		<!-- Price & Weight -->
		<div class="flex justify-between items-center">
			<div class="font-bold text-gray-900 text-lg">
				{#if bean.price}
					{bean.currency === 'GBP' ? '£' : bean.currency === 'EUR' ? '€' : '$'}{bean.price}
				{:else}
					<span class="text-gray-400">Price not available</span>
				{/if}
			</div>
			<div class="text-gray-500 text-sm">
				{#if bean.weight}
					{bean.weight}g
				{/if}
			</div>
		</div>

		<!-- Stock Status -->
		{#if bean.in_stock !== null}
			<div class="mt-2">
				<span
					class="inline-block px-2 py-1 rounded font-medium text-xs"
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
