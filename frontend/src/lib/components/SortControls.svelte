<script lang="ts">
	import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-svelte';

	let { currentSort = 'name', currentOrder = 'asc', onSort }: {
		currentSort?: string;
		currentOrder?: string;
		onSort?: (event: { sortBy: string; sortOrder: string }) => void;
	} = $props();

	// Available sort options
	const sortOptions = [
		{ value: 'name', label: 'Name' },
		{ value: 'roaster', label: 'Roaster' },
		{ value: 'price', label: 'Price' },
		{ value: 'date_added', label: 'Date Added' }
	];

	function handleSortChange(sortBy: string) {
		let sortOrder = 'asc';

		// If clicking the same sort field, toggle order
		if (sortBy === currentSort) {
			sortOrder = currentOrder === 'asc' ? 'desc' : 'asc';
		} else {
			// Default order for different fields
			if (sortBy === 'price' || sortBy === 'date_added') {
				sortOrder = 'desc';
			}
		}

		onSort?.({ sortBy, sortOrder });
	}

	function getSortIcon(sortBy: string) {
		if (sortBy !== currentSort) {
			return ArrowUpDown;
		}
		return currentOrder === 'asc' ? ArrowUp : ArrowDown;
	}

</script>

<div class="flex items-center space-x-2">
	<span class="font-medium text-gray-700 dark:text-cyan-300 text-sm">Sort by:</span>

	<!-- Desktop sort buttons -->
	<div class="hidden sm:flex items-center space-x-1">
		{#each sortOptions as option}
			{@const IconComponent = getSortIcon(option.value)}
			<button
				class="flex items-center h-10 px-3 py-2 text-sm font-medium rounded-md transition-colors {option.value === currentSort
					? 'bg-orange-100 dark:bg-emerald-900/60 text-orange-700 dark:text-emerald-300 border border-orange-200 dark:border-emerald-500/50'
					: 'text-gray-600 dark:text-cyan-300 bg-white dark:bg-slate-700/60 border border-gray-200 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-600/60'}"
				onclick={() => handleSortChange(option.value)}
			>
				<span class="mr-1">{option.label}</span>
				<IconComponent
					class="w-3 h-3 {option.value === currentSort ? 'text-orange-600 dark:text-emerald-400' : 'text-gray-400 dark:text-cyan-400/70'}"
				/>
			</button>
		{/each}
	</div>

	<!-- Mobile sort dropdown -->
	<div class="sm:hidden">
		<select
			class="bg-white dark:bg-slate-700 px-3 py-2 border border-gray-200 focus:border-orange-500 dark:border-slate-600 dark:focus:border-emerald-500 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500 dark:focus:ring-emerald-500/50 h-10 text-gray-900 dark:text-cyan-200 text-sm"
			value={`${currentSort}-${currentOrder}`}
			onchange={(e) => {
				const [sortBy, sortOrder] = e.currentTarget.value.split('-');
				onSort?.({ sortBy, sortOrder });
			}}
		>
			{#each sortOptions as option}
				<option value="{option.value}-asc" class="dark:bg-slate-700 dark:text-cyan-200">{option.label} (A-Z)</option>
				<option value="{option.value}-desc" class="dark:bg-slate-700 dark:text-cyan-200">{option.label} (Z-A)</option>
			{/each}
		</select>
	</div>
</div>
