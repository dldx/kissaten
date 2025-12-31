<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { Coffee, Clock } from "lucide-svelte";
	import { page } from "$app/stores";

	let { data, children } = $props();

	let currentPath = $derived($page.url.pathname);
	let isSavedRoute = $derived(currentPath.includes('/saved'));
	let isRecentRoute = $derived(currentPath.includes('/recently-viewed'));
</script>

<svelte:head>
	<title>My Coffee Vault - Kissaten</title>
	<meta
		name="description"
		content="Your saved coffee beans and tasting notes"
	/>
</svelte:head>

<div class="mx-auto px-4 py-8 max-w-7xl container">
	<!-- Header -->
	<div class="mb-12 text-center">
		<h1
			class="varietal-title-shadow mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl"
		>
			My Coffee Vault
		</h1>

		<!-- Tabs -->
		<div class="flex justify-center gap-2 mb-6">
			<Button
				variant={isSavedRoute ? 'default' : 'outline'}
				href="/vault/saved"
			>
				<Coffee class="mr-2 w-4 h-4" />
				Saved Beans
			</Button>
			<Button
				variant={isRecentRoute ? 'default' : 'outline'}
				href="/vault/recently-viewed"
			>
				<Clock class="mr-2 w-4 h-4" />
				Recently Viewed
			</Button>
		</div>
		<div
			class="p-2 border border-red-500 dark:border-red-500/80 rounded-lg text-red-500 dark:text-red-500/80 text-sm"
		>
			Please note: kissaten is still in beta. Some features may not work
			perfectly and there may be bugs. If you find any, please <a
				href="https://github.com/dldx/kissaten/issues"
				target="_blank"
				class="underline">let me know</a
			>!
		</div>
	</div>

	{@render children()}
</div>
