<script lang="ts">
	import type { PaginationInfo } from '$lib/api';
	import { ChevronLeft, ChevronRight } from 'lucide-svelte';

	let { pagination, onPageChange }: {
		pagination: PaginationInfo;
		onPageChange?: (page: number) => void;
	} = $props();

	function goToPage(page: number) {
		if (page >= 1 && page <= pagination.total_pages) {
			onPageChange?.(page);
		}
	}

	// Generate page numbers to show
	function getPageNumbers() {
		const { page, total_pages } = pagination;
		const delta = 2; // Number of pages to show on each side of current page
		const range = [];
		const rangeWithDots = [];

		// Always include first page
		range.push(1);

		// Add pages around current page
		for (let i = Math.max(2, page - delta); i <= Math.min(total_pages - 1, page + delta); i++) {
			range.push(i);
		}

		// Always include last page (if not page 1)
		if (total_pages > 1) {
			range.push(total_pages);
		}

		// Remove duplicates and sort
		const uniqueRange = [...new Set(range)].sort((a, b) => a - b);

		// Add dots where there are gaps
		let lastPage = 0;
		for (const pageNum of uniqueRange) {
			if (lastPage && pageNum - lastPage > 1) {
				rangeWithDots.push('...');
			}
			rangeWithDots.push(pageNum);
			lastPage = pageNum;
		}

		return rangeWithDots;
	}

	const pageNumbers = $derived(getPageNumbers());
</script>

<div class="flex justify-between items-center">
	<!-- Previous button -->
	<button
		class="flex items-center bg-white hover:bg-gray-50 disabled:opacity-50 px-3 py-2 border border-gray-300 rounded-md font-medium text-gray-500 hover:text-gray-700 text-sm disabled:cursor-not-allowed"
		disabled={!pagination.has_previous}
		onclick={() => goToPage(pagination.page - 1)}
	>
		<ChevronLeft class="mr-1 w-4 h-4" />
		Previous
	</button>

	<!-- Page numbers -->
	<div class="hidden sm:flex items-center space-x-1">
		{#each pageNumbers as pageNum}
			{#if pageNum === '...'}
				<span class="px-3 py-2 text-gray-500 text-sm">...</span>
			{:else}
				<button
					class="px-3 py-2 text-sm font-medium rounded-md transition-colors {pageNum === pagination.page
						? 'bg-orange-600 text-white'
						: 'text-gray-700 bg-white border border-gray-300 hover:bg-gray-50'}"
					onclick={() => goToPage(pageNum as number)}
				>
					{pageNum}
				</button>
			{/if}
		{/each}
	</div>

	<!-- Current page info (mobile) -->
	<div class="sm:hidden flex items-center">
		<span class="text-gray-700 text-sm">
			Page {pagination.page} of {pagination.total_pages}
		</span>
	</div>

	<!-- Next button -->
	<button
		class="flex items-center bg-white hover:bg-gray-50 disabled:opacity-50 px-3 py-2 border border-gray-300 rounded-md font-medium text-gray-500 hover:text-gray-700 text-sm disabled:cursor-not-allowed"
		disabled={!pagination.has_next}
		onclick={() => goToPage(pagination.page + 1)}
	>
		Next
		<ChevronRight class="ml-1 w-4 h-4" />
	</button>
</div>

<!-- Additional info -->
<div class="mt-4 text-center">
	<p class="text-gray-600 text-sm">
		Showing {((pagination.page - 1) * pagination.per_page) + 1}–{Math.min(pagination.page * pagination.per_page, pagination.total_items)}
		of {pagination.total_items.toLocaleString()} results
	</p>
</div>
