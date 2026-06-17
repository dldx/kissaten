<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import { HistoryIcon, Library } from "lucide-svelte";
	import CoffeeBeanIcon from "virtual:icons/grommet-icons/coffee";
	import { page } from "$app/state";

	let { data, children } = $props();

	let currentPath = $derived(page.url.pathname);
	let isSavedRoute = $derived(currentPath.includes('/saved'));
	let isRecentRoute = $derived(currentPath.includes('/recently-viewed'));
	let isCustomRoute = $derived(currentPath.includes('/collection'));
</script>

<svelte:head>
	<title>My Coffee Vault | Kissaten</title>
	<meta
		name="description"
		content="Your saved coffee beans and tasting notes"
	/>
	<meta name="robots" content="noindex,follow" />
	<link rel="canonical" href="https://kissaten.app/vault/saved" />
</svelte:head>

<div class="mx-auto px-4 py-8 max-w-7xl container">
	<!-- Header -->
	<div class="mb-12 text-center" style="view-transition-name: vault-header">
		<h1
			class="varietal-title-shadow mb-4 font-bold text-gray-900 dark:text-cyan-100 text-4xl md:text-5xl"
		>
			My Coffee Vault
		</h1>

		<!-- Tabs -->
		<div class="flex flex-row justify-center gap-1.5 sm:gap-2 mb-6 w-full">
			<Button
				variant={isSavedRoute ? 'default' : 'outline'}
				href="/vault/saved"
				class="flex md:flex-row flex-col items-center gap-1 md:gap-2 px-3 md:px-4 py-2.5 md:py-2 h-auto text-xs md:text-sm"
			>
				<CoffeeBeanIcon class="w-4 h-4" />
				<span>Saved Beans</span>
			</Button>
			<Button
				variant={isCustomRoute ? 'default' : 'outline'}
				href="/vault/collection"
				class="flex md:flex-row flex-col items-center gap-1 md:gap-2 px-3 md:px-4 py-2.5 md:py-2 h-auto text-xs md:text-sm"
			>
				<Library class="w-4 h-4" />
				<span><span class="hidden md:inline">Private&nbsp;</span>Collection</span>
			</Button>
			<Button
				variant={isRecentRoute ? 'default' : 'outline'}
				href="/vault/recently-viewed"
				class="flex md:flex-row flex-col items-center gap-1 md:gap-2 px-3 md:px-4 py-2.5 md:py-2 h-auto text-xs md:text-sm"
			>
				<HistoryIcon class="w-4 h-4" />
				<span class="text-center">Recently Viewed</span>
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
