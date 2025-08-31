<script lang="ts">
	import type { Varietal } from '$lib/api';
	import 'iconify-icon';

	let { varietal }: { varietal: Varietal } = $props();

	const href = $derived(`/varietals/${varietal.slug}`);
</script>

<a
	{href}
	class="group block bg-white hover:shadow-lg p-4 border border-gray-200 hover:border-gray-300 rounded-lg transition-all duration-200"
>
	<div class="flex flex-col h-full">
		<!-- Varietal Name -->
		<h3 class="mb-2 font-semibold text-gray-900 group-hover:text-orange-600 line-clamp-2 transition-colors">
			{varietal.name}
		</h3>

		<!-- Statistics -->
		<div class="flex-grow">
			<div class="space-y-2 text-gray-600 text-sm">
				<div class="flex justify-between">
					<span>Beans:</span>
					<span class="font-medium text-gray-900">
						{varietal.bean_count.toLocaleString()}
					</span>
				</div>

				<!-- Countries with flags -->
				<div class="space-y-1">
					<div class="flex justify-between items-center">
						<span>Countries:</span>
					{#if varietal.countries && varietal.countries.length > 0}
						<div class="flex flex-wrap justify-end gap-1">
							{#each varietal.countries as country}
								<iconify-icon
									icon="circle-flags:{country.country_code.toLowerCase()}"
									width="16"
									height="16"
									title={country.country_name}
									class="rounded-sm"
								></iconify-icon>
							{/each}
						</div>
					{/if}
					</div>
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
		line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
