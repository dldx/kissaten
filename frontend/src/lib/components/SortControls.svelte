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
		{ value: 'scraped_at', label: 'Date Added' }
	];

	function handleSortChange(sortBy: string) {
		let sortOrder = 'asc';

		// If clicking the same sort field, toggle order
		if (sortBy === currentSort) {
			sortOrder = currentOrder === 'asc' ? 'desc' : 'asc';
		} else {
			// Default order for different fields
			if (sortBy === 'price' || sortBy === 'scraped_at') {
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

	function getSortLabel(option: { value: string; label: string }) {
		const isActive = option.value === currentSort;
		const orderText = isActive ? (currentOrder === 'asc' ? '↑' : '↓') : '';
		return `${option.label} ${orderText}`.trim();
	}
</script>

<div class="flex items-center space-x-2">
	<span class="font-medium text-gray-700 text-sm">Sort by:</span>

	<!-- Desktop sort buttons -->
	<div class="hidden sm:flex items-center space-x-1">
		{#each sortOptions as option}
			{@const IconComponent = getSortIcon(option.value)}
			<button
				class="flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors {option.value === currentSort
					? 'bg-orange-100 text-orange-700 border border-orange-200'
					: 'text-gray-600 bg-white border border-gray-200 hover:bg-gray-50'}"
				onclick={() => handleSortChange(option.value)}
			>
				<span class="mr-1">{option.label}</span>
				<IconComponent
					class="w-3 h-3 {option.value === currentSort ? 'text-orange-600' : 'text-gray-400'}"
				/>
			</button>
		{/each}
	</div>

	<!-- Mobile sort dropdown -->
	<div class="sm:hidden">
		<select
			class="bg-white px-3 py-2 border border-gray-200 focus:border-orange-500 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm"
			value={`${currentSort}-${currentOrder}`}
			onchange={(e) => {
				const [sortBy, sortOrder] = e.currentTarget.value.split('-');
				onSort?.({ sortBy, sortOrder });
			}}
		>
			{#each sortOptions as option}
				<option value="{option.value}-asc">{option.label} (A-Z)</option>
				<option value="{option.value}-desc">{option.label} (Z-A)</option>
			{/each}
		</select>
	</div>
</div>
