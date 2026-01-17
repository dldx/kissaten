<script lang="ts">
	import type { ProcessCategory } from "$lib/api";
	import ProcessCard from "./ProcessCard.svelte";
	import { categoryConfig } from "$lib/config/process-categories";
	import { onMount } from "svelte";

	let {
		categoryKey,
		category,
	}: { categoryKey: string; category: ProcessCategory } = $props();

	let config = $derived(categoryConfig[categoryKey] || categoryConfig.other);
	let colorClasses = $derived(getColorClasses(config.color));

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

	function getColorClasses(color: string) {
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
				border: "border-blue-200",
				bg: "bg-blue-50",
				headerBg: "bg-blue-100",
				text: "text-blue-900",
				count: "text-blue-700",
			},
			yellow: {
				border: "border-yellow-200",
				bg: "bg-yellow-50",
				headerBg: "bg-yellow-100",
				text: "text-yellow-900",
				count: "text-yellow-700",
			},
			purple: {
				border: "border-purple-200",
				bg: "bg-purple-50",
				headerBg: "bg-purple-100",
				text: "text-purple-900",
				count: "text-purple-700",
			},
			amber: {
				border: "border-amber-200",
				bg: "bg-amber-50",
				headerBg: "bg-amber-100",
				text: "text-amber-900",
				count: "text-amber-700",
			},
			green: {
				border: "border-green-200",
				bg: "bg-green-50",
				headerBg: "bg-green-100",
				text: "text-green-900",
				count: "text-green-700",
			},
			pink: {
				border: "border-pink-200",
				bg: "bg-pink-50",
				headerBg: "bg-pink-100",
				text: "text-pink-900",
				count: "text-pink-700",
			},
			gray: {
				border: "border-gray-200",
				bg: "bg-gray-50",
				headerBg: "bg-gray-100",
				text: "text-gray-900",
				count: "text-gray-700",
			},
		};
		return classes[color] || classes.gray;
	}

	// Sort processes by bean count descending
	let sortedProcesses = $derived(
		[...category.processes].sort((a, b) => b.bean_count - a.bean_count),
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
						class="text-xl font-bold {colorClasses.text} process-category-title-shadow process-category-title-dark flex items-center gap-2 scroll-mt-24"
						id={category.name.toLowerCase().replace(" ", "-")}
					>
						<span
							class="process-category-icon-shadow text-2xl"
							aria-hidden="true">{config.icon}</span
						>
						{category.name}
					</h2>
					<p
						class="text-sm {colorClasses.count} process-bean-count-shadow process-category-count-dark"
					>
						{category.total_beans.toLocaleString()} total beans
					</p>
				</div>
			</div>
			<div class="text-right">
				<div
					class="text-2xl font-bold {colorClasses.text} process-count-shadow process-category-title-dark"
				>
					{category.processes.length}
				</div>
				<div
					class="text-xs {colorClasses.count} uppercase tracking-wide process-category-count-dark"
				>
					processes
				</div>
			</div>
		</div>
		<p
			class="mt-2 text-sm {colorClasses.count} process-category-description-shadow process-category-description-dark"
		>
			{config.shortDescription}
		</p>
	</div>

	<!-- Processes Grid -->
	<div class="p-6">
		<div
			class="gap-4 grid grid-cols-2 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
		>
			{#if isVisible}
				{#each sortedProcesses as process}
					<ProcessCard {process} />
				{/each}
			{:else}
				<!-- Skeleton placeholders to prevent layout shift -->
				{#each sortedProcesses as _}
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
