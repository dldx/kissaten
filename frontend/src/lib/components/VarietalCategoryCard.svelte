<script lang="ts">
	import type { VarietalCategory } from "$lib/api";
	import VarietalCard from "./VarietalCard.svelte";
	import { varietalConfig } from "$lib/config/varietal-categories";
	import { onMount } from "svelte";

	let {
		categoryKey,
		category,
	}: { categoryKey: string; category: VarietalCategory } = $props();

	const config = $derived(
		varietalConfig[categoryKey] || varietalConfig.other,
	);
	const colorClasses = $derived(getColorClasses(config.color));

	let isVisible = $state(false);
	let categoryElement: HTMLDivElement;

	onMount(() => {
		const observer = new IntersectionObserver(
			(entries) => {
				entries.forEach((entry) => {
					if (entry.isIntersecting) {
						isVisible = true;
						// Once visible, we don't need to observe anymore
						observer.disconnect();
					}
				});
			},
			{
				rootMargin: "100px", // Start loading slightly before element comes into view
				threshold: 0,
			},
		);

		if (categoryElement) {
			observer.observe(categoryElement);
		}

		return () => {
			observer.disconnect();
		};
	});

	function getColorClasses(color: string): {
		border: string;
		bg: string;
		headerBg: string;
		text: string;
		count: string;
	} {
		const classes: Record<
			string,
			{
				border: string;
				bg: string;
				headerBg: string;
				text: string;
				count: string;
			}
		> = {
			blue: {
				border: "border-blue-200 dark:border-cyan-500/30",
				bg: "bg-blue-50 dark:bg-slate-800/60",
				headerBg: "bg-blue-100 dark:bg-cyan-900/40",
				text: "text-blue-900 dark:text-cyan-200",
				count: "text-blue-700 dark:text-cyan-300",
			},
			yellow: {
				border: "border-yellow-200 dark:border-yellow-500/30",
				bg: "bg-yellow-50 dark:bg-slate-800/60",
				headerBg: "bg-yellow-100 dark:bg-yellow-900/40",
				text: "text-yellow-900 dark:text-yellow-200",
				count: "text-yellow-700 dark:text-yellow-300",
			},
			purple: {
				border: "border-purple-200 dark:border-purple-500/30",
				bg: "bg-purple-50 dark:bg-slate-800/60",
				headerBg: "bg-purple-100 dark:bg-purple-900/40",
				text: "text-purple-900 dark:text-purple-200",
				count: "text-purple-700 dark:text-purple-300",
			},
			amber: {
				border: "border-amber-200 dark:border-amber-500/30",
				bg: "bg-amber-50 dark:bg-slate-800/60",
				headerBg: "bg-amber-100 dark:bg-amber-900/40",
				text: "text-amber-900 dark:text-amber-200",
				count: "text-amber-700 dark:text-amber-300",
			},
			green: {
				border: "border-green-200 dark:border-emerald-500/30",
				bg: "bg-green-50 dark:bg-slate-800/60",
				headerBg: "bg-green-100 dark:bg-emerald-900/40",
				text: "text-green-900 dark:text-emerald-200",
				count: "text-green-700 dark:text-emerald-300",
			},
			pink: {
				border: "border-pink-200 dark:border-pink-500/30",
				bg: "bg-pink-50 dark:bg-slate-800/60",
				headerBg: "bg-pink-100 dark:bg-pink-900/40",
				text: "text-pink-900 dark:text-pink-200",
				count: "text-pink-700 dark:text-pink-300",
			},
			indigo: {
				border: "border-indigo-200 dark:border-indigo-500/30",
				bg: "bg-indigo-50 dark:bg-slate-800/60",
				headerBg: "bg-indigo-100 dark:bg-indigo-900/40",
				text: "text-indigo-900 dark:text-indigo-200",
				count: "text-indigo-700 dark:text-indigo-300",
			},
			orange: {
				border: "border-orange-200 dark:border-orange-500/30",
				bg: "bg-orange-50 dark:bg-slate-800/60",
				headerBg: "bg-orange-100 dark:bg-orange-900/40",
				text: "text-orange-900 dark:text-orange-200",
				count: "text-orange-700 dark:text-orange-300",
			},
			gray: {
				border: "border-gray-200 dark:border-gray-500/30",
				bg: "bg-gray-50 dark:bg-slate-800/60",
				headerBg: "bg-gray-100 dark:bg-gray-900/40",
				text: "text-gray-900 dark:text-gray-200",
				count: "text-gray-700 dark:text-gray-300",
			},
		};
		return classes[color] || classes.gray;
	}

	// Sort varietals by bean count descending
	const sortedVarietals = $derived(
		[...category.varietals].sort((a, b) => b.bean_count - a.bean_count),
	);
</script>

<div
	bind:this={categoryElement}
	class="border {colorClasses.border} {colorClasses.bg} rounded-xl process-category-card-shadow process-category-card-dark"
>
	<!-- Category Header -->
	<div
		class="px-6 py-4 {colorClasses.headerBg} border-b {colorClasses.border} rounded-t-xl process-category-header-dark"
	>
		<div class="flex justify-between items-center">
			<div class="flex items-center space-x-3">
				<div>
					<h2
						class="varietal-category-title-shadow text-xl font-bold {colorClasses.text} flex items-center gap-2 scroll-mt-24"
						id={category.name.toLowerCase().replace(" ", "-")}
					>
						<span class="text-2xl" aria-hidden="true"
							>{config.icon}</span
						>
						{category.name}
					</h2>
					<p
						class="varietal-category-description-shadow text-sm {colorClasses.count}"
					>
						{category.total_beans.toLocaleString()} total beans
					</p>
				</div>
			</div>
			<div class="text-right">
				<div
					class="varietal-count-shadow text-2xl font-bold {colorClasses.text}"
				>
					{category.varietals.length}
				</div>
				<div
					class="varietal-category-description-shadow text-xs {colorClasses.count} uppercase tracking-wide"
				>
					varietals
				</div>
			</div>
		</div>
		<p
			class="varietal-category-description-shadow mt-2 text-sm {colorClasses.count}"
		>
			{config.shortDescription}
		</p>
	</div>

	<!-- Varietals Grid -->
	<div class="p-2 sm:p-6">
		<div
			class="gap-4 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
		>
			{#if isVisible}
				{#each sortedVarietals as varietal}
					<VarietalCard {varietal} />
				{/each}
			{:else}
				<!-- Skeleton placeholders to prevent layout shift -->
				{#each sortedVarietals as _}
					<div
						class="flex flex-col bg-white dark:bg-slate-800/80 border border-gray-200 dark:border-cyan-500/30 rounded-lg animate-pulse"
					>
						<!-- Header placeholder -->
						<div
							class="bg-gray-200 dark:bg-slate-700 rounded-t-lg w-full h-24 sm:h-32"
						></div>
						<!-- Content placeholder -->
						<div class="space-y-3 p-3 sm:p-4">
							<div
								class="bg-gray-200 dark:bg-slate-700 rounded w-3/4 h-4"
							></div>
							<div
								class="bg-gray-200 dark:bg-slate-700 rounded w-1/2 h-3"
							></div>
							<div class="space-y-2">
								<div
									class="bg-gray-200 dark:bg-slate-700 rounded w-full h-3"
								></div>
								<div
									class="bg-gray-200 dark:bg-slate-700 rounded w-5/6 h-3"
								></div>
							</div>
							<div class="flex gap-2 pt-2">
								<div
									class="flex-1 bg-gray-200 dark:bg-slate-700 rounded h-8 sm:h-9"
								></div>
								<div
									class="flex-1 bg-gray-200 dark:bg-slate-700 rounded h-8 sm:h-9"
								></div>
							</div>
						</div>
					</div>
				{/each}
			{/if}
		</div>
	</div>
</div>
