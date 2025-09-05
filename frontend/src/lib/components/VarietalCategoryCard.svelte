<script lang="ts">
	import type { VarietalCategory } from '$lib/api';
	import VarietalCard from './VarietalCard.svelte';

	let { categoryKey, category }: { categoryKey: string; category: VarietalCategory } = $props();

	// Category display configuration
	const categoryConfig: Record<string, { icon: string; color: string; description: string }> = {
		typica: {
			icon: '🌱',
			color: 'green',
			description: 'Classic heritage variety known for exceptional cup quality and complex flavors'
		},
		bourbon: {
			icon: '🍇',
			color: 'purple',
			description: 'Sweet, balanced varieties with rich body and wine-like characteristics'
		},
		heirloom: {
			icon: '🏛️',
			color: 'amber',
			description: 'Indigenous and wild varieties with unique regional characteristics'
		},
		geisha: {
			icon: '🌸',
			color: 'pink',
			description: 'Prized variety known for exceptional floral and jasmine-like flavors'
		},
		sl_varieties: {
			icon: '🔬',
			color: 'blue',
			description: 'Scott Labs selections bred for disease resistance and quality'
		},
		hybrid: {
			icon: '🧬',
			color: 'indigo',
			description: 'Modern cultivars bred for productivity and environmental resilience'
		},
		large_bean: {
			icon: '🫘',
			color: 'yellow',
			description: 'Varieties producing notably large beans with unique characteristics'
		},
		arabica_other: {
			icon: '☕',
			color: 'orange',
			description: 'Other distinct Arabica varieties with specialized characteristics'
		},
		other: {
			icon: '❓',
			color: 'gray',
			description: 'Unique and specialty coffee varieties'
		}
	};

	const config = $derived(categoryConfig[categoryKey] || categoryConfig.other);
	const colorClasses = $derived(getColorClasses(config.color));

	function getColorClasses(color: string): {
		border: string;
		bg: string;
		headerBg: string;
		text: string;
		count: string;
	} {
		const classes: Record<string, {
			border: string;
			bg: string;
			headerBg: string;
			text: string;
			count: string;
		}> = {
			blue: {
				border: 'border-blue-200 dark:border-cyan-500/30',
				bg: 'bg-blue-50 dark:bg-slate-800/60',
				headerBg: 'bg-blue-100 dark:bg-cyan-900/40',
				text: 'text-blue-900 dark:text-cyan-200',
				count: 'text-blue-700 dark:text-cyan-300'
			},
			yellow: {
				border: 'border-yellow-200 dark:border-yellow-500/30',
				bg: 'bg-yellow-50 dark:bg-slate-800/60',
				headerBg: 'bg-yellow-100 dark:bg-yellow-900/40',
				text: 'text-yellow-900 dark:text-yellow-200',
				count: 'text-yellow-700 dark:text-yellow-300'
			},
			purple: {
				border: 'border-purple-200 dark:border-purple-500/30',
				bg: 'bg-purple-50 dark:bg-slate-800/60',
				headerBg: 'bg-purple-100 dark:bg-purple-900/40',
				text: 'text-purple-900 dark:text-purple-200',
				count: 'text-purple-700 dark:text-purple-300'
			},
			amber: {
				border: 'border-amber-200 dark:border-amber-500/30',
				bg: 'bg-amber-50 dark:bg-slate-800/60',
				headerBg: 'bg-amber-100 dark:bg-amber-900/40',
				text: 'text-amber-900 dark:text-amber-200',
				count: 'text-amber-700 dark:text-amber-300'
			},
			green: {
				border: 'border-green-200 dark:border-emerald-500/30',
				bg: 'bg-green-50 dark:bg-slate-800/60',
				headerBg: 'bg-green-100 dark:bg-emerald-900/40',
				text: 'text-green-900 dark:text-emerald-200',
				count: 'text-green-700 dark:text-emerald-300'
			},
			pink: {
				border: 'border-pink-200 dark:border-pink-500/30',
				bg: 'bg-pink-50 dark:bg-slate-800/60',
				headerBg: 'bg-pink-100 dark:bg-pink-900/40',
				text: 'text-pink-900 dark:text-pink-200',
				count: 'text-pink-700 dark:text-pink-300'
			},
			indigo: {
				border: 'border-indigo-200 dark:border-indigo-500/30',
				bg: 'bg-indigo-50 dark:bg-slate-800/60',
				headerBg: 'bg-indigo-100 dark:bg-indigo-900/40',
				text: 'text-indigo-900 dark:text-indigo-200',
				count: 'text-indigo-700 dark:text-indigo-300'
			},
			orange: {
				border: 'border-orange-200 dark:border-orange-500/30',
				bg: 'bg-orange-50 dark:bg-slate-800/60',
				headerBg: 'bg-orange-100 dark:bg-orange-900/40',
				text: 'text-orange-900 dark:text-orange-200',
				count: 'text-orange-700 dark:text-orange-300'
			},
			gray: {
				border: 'border-gray-200 dark:border-gray-500/30',
				bg: 'bg-gray-50 dark:bg-slate-800/60',
				headerBg: 'bg-gray-100 dark:bg-gray-900/40',
				text: 'text-gray-900 dark:text-gray-200',
				count: 'text-gray-700 dark:text-gray-300'
			}
		};
		return classes[color] || classes.gray;
	}

	// Sort varietals by bean count descending
	const sortedVarietals = $derived([...category.varietals].sort((a, b) => b.bean_count - a.bean_count));
</script>

<div class="border {colorClasses.border} {colorClasses.bg} rounded-xl overflow-hidden">
	<!-- Category Header -->
	<div class="px-6 py-4 {colorClasses.headerBg} border-b {colorClasses.border}">
		<div class="flex justify-between items-center">
			<div class="flex items-center space-x-3">
				<span class="text-2xl" aria-hidden="true">{config.icon}</span>
				<div>
					<h2 class="varietal-category-title-shadow text-xl font-bold {colorClasses.text}">
						{category.name}
					</h2>
					<p class="varietal-category-description-shadow text-sm {colorClasses.count}">
						{category.total_beans.toLocaleString()} total beans
					</p>
				</div>
			</div>
			<div class="text-right">
				<div class="varietal-count-shadow text-2xl font-bold {colorClasses.text}">
					{category.varietals.length}
				</div>
				<div class="varietal-category-description-shadow text-xs {colorClasses.count} uppercase tracking-wide">
					varietals
				</div>
			</div>
		</div>
		<p class="varietal-category-description-shadow mt-2 text-sm {colorClasses.count}">
			{config.description}
		</p>
	</div>

	<!-- Varietals Grid -->
	<div class="p-6">
		<div class="gap-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
			{#each sortedVarietals as varietal}
				<VarietalCard {varietal} />
			{/each}
		</div>
	</div>
</div>
