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
	import { formatPrice, getFlavourCategoryColors } from "$lib/utils";
	import "iconify-icon";
	import {
		Droplets,
		Leaf,
		Flame,
		Coffee,
		Star,
		Ban,
		Combine,
		Calendar,
		Trash2,
		ExternalLink,
	} from "lucide-svelte";
	import beanSvg from "./bean.svg?raw";
	import { Button } from "$lib/components/ui/button";
	import BeanNotesEditor from "./vault/BeanNotesEditor.svelte";

	interface Props {
		bean: CoffeeBean & {
			savedAt?: string;
			savedBeanId?: string;
			notes?: string;
		};
		class?: string;
		// Vault-specific props (optional)
		vaultMode?: boolean;
		onRemove?: (savedBeanId: string) => void;
		onNotesChange?: (notes: string) => void;
	}

	let {
		bean,
		class: className = "",
		vaultMode = false,
		onRemove,
		onNotesChange,
	}: Props = $props();

	// Helper to get display data from origins
	const primaryOrigin = $derived(api.getPrimaryOrigin(bean));
	const originDisplay = $derived(api.getOriginDisplayString(bean));
	const processes = $derived(api.getBeanProcesses(bean));
	const varieties = $derived(api.getVarieties(bean));

	// Check if bean is new (added within the last week)
	const isNewBean = $derived.by(() => {
		if (!bean.date_added) return false;
		const dateAdded = new Date(bean.date_added);
		const oneWeekAgo = new Date();
		oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
		return dateAdded > oneWeekAgo;
	});
</script>

<Card
	class={`hover:shadow-lg dark:hover:shadow-cyan-500/20 dark:hover:shadow-2xl transition-all duration-300 ${vaultMode ? "" : "cursor-pointer"} dark:border-cyan-500/30 dark:bg-gradient-to-br dark:from-slate-900/80 dark:to-slate-800/80 dark:hover:border-cyan-400/60 dark:hover:-translate-y-1 ${className}`}
>
	<CardHeader class="relative p-0 overflow-hidden">
		<!-- Image Section - Emphasized -->
		<CoffeeBeanImage
			{bean}
			class="dark:opacity-90 rounded-t-lg w-full h-full aspect-[4/3]"
		/>

		<!-- New Bean Banner - Diagonal Left -->
		{#if isNewBean}
			<div
				class="top-0 left-0 z-10 absolute w-10 h-10"
				title="Released within the last week!"
			>
				<div
					class="top-1 -left-8 absolute flex justify-center items-center bg-yellow-400 dark:bg-yellow-500 shadow-lg w-24 h-6 font-(family-name:--font-fun) text-yellow-900 dark:text-yellow-900 text-xs -rotate-45 origin-center transform"
				>
					{@html beanSvg}
				</div>
			</div>
		{/if}

		<div class="p-4 pb-2">
			<CardTitle
				class="bean-title-shadow mb-1 font-semibold text-gray-900 dark:text-cyan-100 text-base line-clamp-2"
			>
				{bean.name}
			</CardTitle>

			<CardDescription
				class="bean-description-shadow text-gray-600 dark:text-cyan-300/80 text-xs"
			>
				{bean.roaster}, {bean.roaster_country_code}
			</CardDescription>
		</div>
	</CardHeader>

	<CardContent class="p-4 pt-0">
		<!-- Origin Info -->
		<div class="mb-2">
			<div
				class="font-medium text-gray-700 dark:text-emerald-300 text-xs bean-origin-shadow"
			>
				{originDisplay}
			</div>
			{#if primaryOrigin?.elevation_min && primaryOrigin.elevation_min > 0}
				<div class="text-gray-500 dark:text-cyan-400/70 text-xs">
					{#if primaryOrigin.elevation_max && primaryOrigin.elevation_max > primaryOrigin.elevation_min}
						{primaryOrigin.elevation_min}-{primaryOrigin.elevation_max}m
						elevation
					{:else}
						{primaryOrigin.elevation_min}m elevation
					{/if}
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
				<div
					class="bean-tasting-notes-shadow mb-1 font-medium text-gray-700 dark:text-emerald-300 text-xs"
				>
					Tasting Notes
				</div>
				<div class="flex flex-wrap gap-1">
					{#each bean.tasting_notes as note}
						{@const flavourCategoryColors =
							getFlavourCategoryColors(
								typeof note === "string"
									? ""
									: (note.primary_category ?? ""),
							)}
						<span
							class="inline-block {flavourCategoryColors.bg} {flavourCategoryColors.darkBg} {flavourCategoryColors.text} {flavourCategoryColors.darkText} bean-tasting-note-shadow px-1.5 py-0.5 dark:border dark:border-cyan-500/30 rounded text-xs"
						>
							{typeof note === "string" ? note : note.note}
						</span>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Price & Weight -->
		<div class="flex justify-between items-center">
			<div
				class="bean-price-shadow font-bold text-gray-900 dark:text-emerald-300 text-base"
			>
				{#if bean.price}
					{formatPrice(bean.price, bean.currency)}
				{:else}
					<span class="text-gray-400 dark:text-cyan-500/60 text-sm"
						>Price not available</span
					>
				{/if}
			</div>
			<div
				class="bean-weight-shadow text-gray-500 dark:text-cyan-400/80 text-xs"
			>
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

		<!-- Vault Features (shown only when enabled) -->
		{#if vaultMode}
			<!-- Saved Date & Remove Button -->
			<div
				class="flex justify-between items-center mt-3 pt-3 dark:border-cyan-500/20 border-t"
			>
				{#if bean.savedAt}
					<span
						class="flex items-center gap-1 text-gray-600 dark:text-cyan-400/80 text-xs"
					>
						<Calendar class="w-3 h-3" />
						Saved {new Date(bean.savedAt).toLocaleDateString()}
					</span>
				{:else}
					<span></span>
				{/if}
				{#if vaultMode}
					<div class="flex items-center gap-1">
						<Button
							variant="ghost"
							size="sm"
							href={`/roasters${api.getBeanUrlPath(bean)}`}
							onclick={(e) => {
								e.stopPropagation();
							}}
							class="dark:hover:bg-cyan-900/20 h-7 dark:hover:text-cyan-300 dark:text-cyan-400 text-xs"
						>
							<ExternalLink class="mr-1 w-3 h-3" />
							View
						</Button>
						{#if onRemove && bean.savedBeanId}
							<Button
								variant="ghost"
								size="sm"
								onclick={(e) => {
									e.preventDefault();
									e.stopPropagation();
									onRemove(bean.savedBeanId!);
								}}
								class="dark:hover:bg-red-900/20 h-7 dark:hover:text-red-300 dark:text-red-400 text-xs"
							>
								<Trash2 class="mr-1 w-3 h-3" />
								Unsave
							</Button>
						{/if}
					</div>
				{/if}
			</div>

			<!-- Notes Section -->
			{#if bean.savedBeanId}
				<div class="mt-3 pt-3 dark:border-cyan-500/20 border-t">
					<label
						for="notes-{bean.id}"
						class="block mb-2 font-medium text-gray-700 dark:text-emerald-300 text-sm"
					>
						Your Notes
					</label>
					<BeanNotesEditor
						savedBeanId={bean.savedBeanId}
						initialNotes={bean.notes || ""}
						id="notes-{bean.id}"
						textareaClass="min-h-[100px]"
						onNoteChange={onNotesChange}
					/>
				</div>
			{/if}
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
