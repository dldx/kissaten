<script lang="ts">
	import type { ProcessCategory } from '$lib/api';
	import ProcessCard from './ProcessCard.svelte';

	export let categoryKey: string;
	export let category: ProcessCategory;

	// Category display configuration
	const categoryConfig: Record<string, { icon: string; color: string; description: string }> = {
		washed: {
			icon: '🌊',
			color: 'blue',
			description: 'Clean, bright, and acidic profiles with well-defined flavours'
		},
		natural: {
			icon: '☀️',
			color: 'yellow',
			description: 'Fruity, wine-like flavours with more body and sweetness'
		},
		anaerobic: {
			icon: '🫙',
			color: 'purple',
			description: 'Unique, complex flavours from oxygen-free fermentation'
		},
		honey: {
			icon: '🍯',
			color: 'amber',
			description: 'Balanced sweetness between washed and natural processes'
		},
		fermentation: {
			icon: '🦠',
			color: 'green',
			description: 'Enhanced flavours through controlled fermentation techniques'
		},
		decaf: {
			icon: '🚫',
			color: 'gray',
			description: 'Caffeine removed while preserving original flavours'
		},
		experimental: {
			icon: '🧪',
			color: 'pink',
			description: 'Innovative techniques pushing flavour boundaries'
		},
		other: {
			icon: '❓',
			color: 'gray',
			description: 'Unique and specialty processing methods'
		}
	};

	$: config = categoryConfig[categoryKey] || categoryConfig.other;
	$: colorClasses = getColorClasses(config.color);

	function getColorClasses(color: string) {
		const classes = {
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

	// Sort processes by bean count descending
	$: sortedProcesses = [...category.processes].sort((a, b) => b.bean_count - a.bean_count);
</script>

<div class="border {colorClasses.border} {colorClasses.bg} rounded-xl overflow-hidden process-category-card-shadow process-category-card-dark">
	<!-- Category Header -->
	<div class="px-6 py-4 {colorClasses.headerBg} border-b {colorClasses.border} process-category-header-dark">
		<div class="flex justify-between items-center">
			<div class="flex items-center space-x-3">
				<span class="process-category-icon-shadow text-2xl" aria-hidden="true">{config.icon}</span>
				<div>
					<h2 class="text-xl font-bold {colorClasses.text} process-category-title-shadow process-category-title-dark">
						{category.name}
					</h2>
					<p class="text-sm {colorClasses.count} process-bean-count-shadow process-category-count-dark">
						{category.total_beans.toLocaleString()} total beans
					</p>
				</div>
			</div>
			<div class="text-right">
				<div class="text-2xl font-bold {colorClasses.text} process-count-shadow process-category-title-dark">
					{category.processes.length}
				</div>
				<div class="text-xs {colorClasses.count} uppercase tracking-wide process-category-count-dark">
					processes
				</div>
			</div>
		</div>
		<p class="mt-2 text-sm {colorClasses.count} process-category-description-shadow process-category-description-dark">
			{config.description}
		</p>
	</div>

	<!-- Processes Grid -->
	<div class="p-6">
		<div class="gap-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
			{#each sortedProcesses as process}
				<ProcessCard {process} />
			{/each}
		</div>
	</div>
</div>
