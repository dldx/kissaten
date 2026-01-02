<script lang="ts">
	import type { PaginationInfo } from '$lib/api';
	import * as Pagination from '$lib/components/ui/pagination/index.js';

	let { pagination, onPageChange }: {
		pagination: PaginationInfo;
		onPageChange?: (page: number) => void;
	} = $props();

	function handlePageChange(pageNum: number) {
		onPageChange?.(pageNum);
	}
</script>

<div class="space-y-4">
	<Pagination.Root
		count={pagination.total_items}
		perPage={pagination.per_page}
		page={pagination.page}
		onPageChange={(page) => handlePageChange(page)}
	>
		{#snippet children({ pages, currentPage })}
			<Pagination.Content>
				<Pagination.Item>
					<Pagination.Previous />
				</Pagination.Item>
				{#each pages as page (page.key)}
					{#if page.type === "ellipsis"}
						<Pagination.Item>
							<Pagination.Ellipsis />
						</Pagination.Item>
					{:else}
						<Pagination.Item>
							<Pagination.Link {page} isActive={currentPage === page.value}>
								{page.value}
							</Pagination.Link>
						</Pagination.Item>
					{/if}
				{/each}
				<Pagination.Item>
					<Pagination.Next />
				</Pagination.Item>
			</Pagination.Content>
		{/snippet}
	</Pagination.Root>

	<!-- Additional info -->
	<div class="text-center">
		<p class="text-gray-600 dark:text-cyan-400/80 text-sm">
			Showing {((pagination.page - 1) * pagination.per_page) + 1}–{Math.min(pagination.page * pagination.per_page, pagination.total_items)}
			of {pagination.total_items.toLocaleString()} results
		</p>
	</div>
</div>
