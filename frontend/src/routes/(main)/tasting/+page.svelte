<script lang="ts">
	import TastingWizard from "$lib/components/tasting/TastingWizard.svelte";
	import type { PageData } from "./$types";

	let { data }: { data: PageData } = $props();
</script>

<svelte:head>
	<title>Guided Coffee Tasting | Kissaten</title>
	<meta name="description" content="A step-by-step guided coffee tasting experience to help you discover new flavours." />
</svelte:head>

<div class="mx-auto px-4 container">
	<TastingWizard savedBeanPaths={data.savedBeanPaths} />
</div>
