<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import {
		Card,
		CardContent,
		CardHeader,
		CardTitle,
	} from "$lib/components/ui/card/index.js";
	import { MapPin } from "lucide-svelte";
	import type { Country } from "$lib/api.js";
	import "iconify-icon";

	interface Props {
		country: Country;
	}

	let { country }: Props = $props();
</script>

<Card
	class="flex flex-col bg-white dark:bg-slate-800/80 hover:shadow-lg dark:hover:shadow-emerald-500/20 border-gray-200 dark:border-slate-600 transition-shadow"
>
	<CardHeader class="p-0">
		<!-- Flag Header Section -->
		<div
			class="flex justify-center items-center bg-gray-50 dark:bg-slate-700/60 p-4 rounded-t-lg w-full h-32"
		>
			<iconify-icon
				icon={`circle-flags:${country.country_code.toLowerCase()}`}
				style="font-size: 96px;"
			></iconify-icon>
		</div>

		<div class="p-8 text-center">
			<CardTitle
				class="mb-1 font-semibold text-gray-900 dark:text-cyan-100 text-base line-clamp-2"
			>
				{country.country_name}
			</CardTitle>
		</div>
	</CardHeader>
	<CardContent class="flex flex-col flex-1 p-4 pt-0">
		<!-- Explore Beans Button -->
		<div class="mt-auto">
			<Button
				class="w-full"
				variant="outline"
				href={`/origins/${country.country_code}`}
			>
				<MapPin class="mr-2 w-4 h-4" />
				Explore {country.bean_count} Bean{country.bean_count === 1
					? ""
					: "s"}
			</Button>
		</div>
	</CardContent>
</Card>
