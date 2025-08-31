<script lang="ts">
	import type { VarietalCategory } from '$lib/api';
	import VarietalCard from './VarietalCard.svelte';

	export let categoryKey: string;
	export let category: VarietalCategory;

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

	$: config = categoryConfig[categoryKey] || categoryConfig.other;
	$: colorClasses = getColorClasses(config.color);

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
				border: 'border-blue-200',
				bg: 'bg-blue-50',
				headerBg: 'bg-blue-100',
				text: 'text-blue-900',
				count: 'text-blue-700'
			},
			yellow: {
				border: 'border-yellow-200',
				bg: 'bg-yellow-50',
				headerBg: 'bg-yellow-100',
				text: 'text-yellow-900',
				count: 'text-yellow-700'
			},
			purple: {
				border: 'border-purple-200',
				bg: 'bg-purple-50',
				headerBg: 'bg-purple-100',
				text: 'text-purple-900',
				count: 'text-purple-700'
			},
			amber: {
				border: 'border-amber-200',
				bg: 'bg-amber-50',
				headerBg: 'bg-amber-100',
				text: 'text-amber-900',
				count: 'text-amber-700'
			},
			green: {
				border: 'border-green-200',
				bg: 'bg-green-50',
				headerBg: 'bg-green-100',
				text: 'text-green-900',
				count: 'text-green-700'
			},
			pink: {
				border: 'border-pink-200',
				bg: 'bg-pink-50',
				headerBg: 'bg-pink-100',
				text: 'text-pink-900',
				count: 'text-pink-700'
			},
			indigo: {
				border: 'border-indigo-200',
				bg: 'bg-indigo-50',
				headerBg: 'bg-indigo-100',
				text: 'text-indigo-900',
				count: 'text-indigo-700'
			},
			orange: {
				border: 'border-orange-200',
				bg: 'bg-orange-50',
				headerBg: 'bg-orange-100',
				text: 'text-orange-900',
				count: 'text-orange-700'
			},
			gray: {
				border: 'border-gray-200',
				bg: 'bg-gray-50',
				headerBg: 'bg-gray-100',
				text: 'text-gray-900',
				count: 'text-gray-700'
			}
		};
		return classes[color] || classes.gray;
	}

	// Sort varietals by bean count descending
	$: sortedVarietals = [...category.varietals].sort((a, b) => b.bean_count - a.bean_count);
</script>

<div class="border {colorClasses.border} {colorClasses.bg} rounded-xl overflow-hidden">
	<!-- Category Header -->
	<div class="px-6 py-4 {colorClasses.headerBg} border-b {colorClasses.border}">
		<div class="flex justify-between items-center">
			<div class="flex items-center space-x-3">
				<span class="text-2xl" aria-hidden="true">{config.icon}</span>
				<div>
					<h2 class="text-xl font-bold {colorClasses.text}">
						{category.name}
					</h2>
					<p class="text-sm {colorClasses.count}">
						{category.total_beans.toLocaleString()} total beans
					</p>
				</div>
			</div>
			<div class="text-right">
				<div class="text-2xl font-bold {colorClasses.text}">
					{category.varietals.length}
				</div>
				<div class="text-xs {colorClasses.count} uppercase tracking-wide">
					varietals
				</div>
			</div>
		</div>
		<p class="mt-2 text-sm {colorClasses.count}">
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
