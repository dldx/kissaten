<script lang="ts">
	import type { Process } from '$lib/api';

	let { process }: { process: Process } = $props();

	const href = $derived(`/process/${process.slug}`);
</script>

<a
	{href}
	class="group block bg-white hover:shadow-lg p-4 border border-gray-200 hover:border-gray-300 rounded-lg transition-all duration-200"
>
	<div class="flex flex-col h-full">
		<!-- Process Name -->
		<h3 class="mb-2 font-semibold text-gray-900 group-hover:text-orange-600 line-clamp-2 transition-colors">
			{process.name}
		</h3>

		<!-- Statistics -->
		<div class="flex-grow">
			<div class="space-y-1 text-gray-600 text-sm">
				<div class="flex justify-between">
					<span>Beans:</span>
					<span class="font-medium text-gray-900">
						{process.bean_count.toLocaleString()}
					</span>
				</div>
				<div class="flex justify-between">
					<span>Roasters:</span>
					<span class="font-medium text-gray-700">
						{process.roaster_count}
					</span>
				</div>
				<div class="flex justify-between">
					<span>Countries:</span>
					<span class="font-medium text-gray-700">
						{process.country_count}
					</span>
				</div>
			</div>
		</div>

		<!-- View Link -->
		<div class="mt-3 pt-3 border-gray-100 border-t">
			<span class="font-medium text-orange-600 group-hover:text-orange-700 text-sm">
				View Details →
			</span>
		</div>
	</div>
</a>

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
